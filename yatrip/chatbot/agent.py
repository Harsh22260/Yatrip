"""
Yatrip AI Agent — LangGraph + Gemini + MCP tools
=================================================

The agent has no hardcoded tool functions. Its entire tool surface is
discovered at runtime from the Yatrip MCP server (``yatrip/mcp_server.py``)
through the Model Context Protocol:

  catalogue  search_hotels, get_hotel_details, check_room_availability,
             search_attractions, search_food, search_rentals,
             find_transport_nodes, nearby_transport_nodes
  open data  geocode_place, reverse_geocode, search_nearby_places,
             get_weather, get_directions, web_search
  RAG        search_knowledge_base

If the MCP server cannot be reached the agent degrades to a plain LLM reply
rather than failing the request.
"""

from __future__ import annotations

import asyncio
import base64
import concurrent.futures
import logging
from datetime import datetime
from typing import Annotated, Any, Sequence, TypedDict

from django.conf import settings
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from chatbot import llm, mcp_client
from yatrip.retry import DailyQuotaExhausted, is_daily_quota_exhausted

logger = logging.getLogger(__name__)

# How much history to replay into the model, in message pairs.
HISTORY_TURNS = 10
VISION_TURNS = 8
MAX_TOOL_ROUNDS = 8

# Provider selection, per-provider throttling and failover all live in
# chatbot.llm so the model can change without touching the agent graph.


SYSTEM_PROMPT = """You are Yatrip AI, a travel assistant for India.

CORE LOGIC (follow strictly):
1. Source hierarchy:
   - Listings that exist on Yatrip come from the `search_*` tools. Use them
     first whenever the user asks about a specific hotel, attraction, food
     place, rental or transport hub.
   - Use `search_knowledge_base` for richer descriptive context about listings.
   - Use `web_search` only for time-sensitive facts (today's weather alerts,
     recent reviews, current event prices, visa rules).
   - Use `geocode_place` / `search_nearby_places` / `get_directions` for
     locations, "what is near me" and route planning.
2. Language: reply in the EXACT same language the user wrote in
   (Hindi, Hinglish or English).
3. Money: always show amounts as ₹ (Indian Rupees).
4. Resilience: tools can fail or a DB may be empty. Never surface a raw tool
   error to the user. If a tool returns no rows or fails, answer from your
   own knowledge instead, and never invent specific prices, addresses or
   phone numbers.
5. Today is {today}.
"""


# Friendly labels for the tools the agent actually called.
TOOL_LABELS = {
    "search_hotels": "🏨 Yatrip Hotels",
    "get_hotel_details": "🏨 Yatrip Hotels",
    "check_room_availability": "📅 Room Availability",
    "search_attractions": "🏛️ Yatrip Attractions",
    "search_food": "🍽️ Yatrip Food",
    "search_rentals": "🏠 Yatrip Rentals",
    "find_transport_nodes": "🚌 Transport Hubs",
    "nearby_transport_nodes": "🚌 Nearby Transport",
    "geocode_place": "🗺️ OpenStreetMap",
    "reverse_geocode": "🗺️ OpenStreetMap",
    "search_nearby_places": "📍 OpenStreetMap Nearby",
    "get_weather": "🌤️ Weather API",
    "get_directions": "🚗 Route Planner",
    "web_search": "🌐 Web Search",
    "search_knowledge_base": "📚 Yatrip Knowledge Base",
}

FALLBACK_ANSWER = (
    "Sorry, I'm having trouble reaching my travel data right now. "
    "Please try again in a moment."
)


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def _system_prompt() -> str:
    return SYSTEM_PROMPT.format(today=datetime.now().strftime("%d %B %Y"))


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------


def _should_continue(state: AgentState) -> str:
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "tools"
    return END


def _limit_tool_rounds(state: AgentState) -> str:
    """Stop looping if the model keeps calling tools without concluding."""
    rounds = sum(1 for message in state["messages"] if getattr(message, "tool_calls", None))
    if rounds > MAX_TOOL_ROUNDS:
        logger.warning("Tool call limit (%d) reached, forcing a final answer", MAX_TOOL_ROUNDS)
        return END
    return "tools"


async def _acall_model(state: AgentState, tools: Sequence[Any]):
    messages = [SystemMessage(content=_system_prompt())] + state["messages"]
    response, _provider = await llm.ainvoke_chain(
        messages, tools=tools, label="agent model call"
    )
    return {"messages": [response]}


async def _abuild_agent(tools: Sequence[Any]):
    async def call_model(state: AgentState):
        return await _acall_model(state, tools)

    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", ToolNode(list(tools)))
    graph.set_entry_point("agent")
    graph.add_conditional_edges(
        "agent",
        _should_continue,
        {"tools": "tools", END: END},
    )
    # A second conditional edge from the tool node is what bounds the loop.
    graph.add_conditional_edges(
        "tools",
        _limit_tool_rounds,
        {"tools": "agent", END: END},
    )
    return graph.compile()


# ---------------------------------------------------------------------------
# Result helpers
# ---------------------------------------------------------------------------


def _collect_tool_usage(messages: list[Any]) -> list[str]:
    used: list[str] = []
    for message in messages:
        for call in getattr(message, "tool_calls", None) or []:
            name = call.get("name") if isinstance(call, dict) else None
            if name and name not in used:
                used.append(name)
    return used


def _label_sources(tool_names_used: Sequence[str]) -> list[str]:
    labels: list[str] = []
    for name in tool_names_used:
        label = TOOL_LABELS.get(name)
        if label and label not in labels:
            labels.append(label)
    return labels


def _answer_of(message: Any) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        return "".join(parts)
    return str(content)


def _vision_answer(query: str, image_data: bytes) -> dict[str, Any]:
    """Images bypass the graph: the model reads them directly."""
    encoded = base64.b64encode(image_data).decode()
    content = [
        {
            "type": "text",
            "text": (
                "Analyse this image in the context of travel in India and "
                f"answer: {query}"
            ),
        },
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
        },
    ]
    messages = [SystemMessage(content=_system_prompt()), HumanMessage(content=content)]
    response, provider = llm.invoke_chain_sync(messages, label="vision model call")
    logger.info("vision answer served by %s", provider)
    return {
        "answer": _answer_of(response),
        "sources": ["🖼️ Image Analysis"],
        "tools_used": ["vision"],
    }

# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def _build_history(chat_history: Sequence[tuple[str, str]] | None) -> list[Any]:
    messages: list[Any] = []
    for human, ai in list(chat_history or [])[-HISTORY_TURNS:]:
        if human:
            messages.append(HumanMessage(content=human))
        if ai:
            messages.append(AIMessage(content=ai))
    return messages


async def _arespond(
    query: str,
    chat_history: Sequence[tuple[str, str]] | None = None,
    image_data: bytes | None = None,
) -> dict[str, Any]:
    if not settings.GEMINI_API_KEY:
        return {"answer": FALLBACK_ANSWER, "sources": [], "tools_used": []}

    # 1. Vision: no tools involved.
    if image_data:
        try:
            return await asyncio.to_thread(_vision_answer, query, image_data)
        except Exception as exc:  # noqa: BLE001
            logger.error("Vision analysis failed: %s", exc)
            return {"answer": FALLBACK_ANSWER, "sources": [], "tools_used": []}

    # 2. Load the tool surface from MCP.
    try:
        tools = await mcp_client.get_tools()
    except mcp_client.McpUnavailable as exc:
        logger.warning("MCP unavailable, answering without tools: %s", exc)
        return await _afallback_answer(query, chat_history)

    if not tools:
        return await _afallback_answer(query, chat_history)

    # 3. Run the graph.
    messages = _build_history(chat_history)
    messages.append(HumanMessage(content=query))

    try:
        agent = await _abuild_agent(tools)
        result = await agent.ainvoke({"messages": messages})
    except Exception as exc:  # noqa: BLE001
        logger.error("Agent run failed, falling back to a plain LLM reply: %s", exc)
        return await _afallback_answer(query, chat_history)

    result_messages = result["messages"]
    tool_names_used = _collect_tool_usage(result_messages)
    return {
        "answer": _answer_of(result_messages[-1]),
        "sources": _label_sources(tool_names_used),
        "tools_used": tool_names_used,
    }


async def _afallback_answer(
    query: str,
    chat_history: Sequence[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    try:
        messages = _build_history(chat_history)[-VISION_TURNS:]
        messages.append(HumanMessage(content=query))
        response, _provider = await llm.ainvoke_chain(
            [SystemMessage(content=_system_prompt())] + messages,
            label="fallback model call",
        )
        return {"answer": _answer_of(response), "sources": [], "tools_used": []}
    except Exception as exc:  # noqa: BLE001
        logger.error("Fallback LLM reply failed: %s", exc)
        return {"answer": _unavailable_message(exc), "sources": [], "tools_used": []}


def _unavailable_message(exc: Exception) -> str:
    """Say *why* the assistant is down instead of a generic apology."""
    if isinstance(exc, llm.AllProvidersExhausted):
        daily = [name for name, why in exc.reasons.items() if why == "daily quota exhausted"]
        if daily and len(daily) == len([r for r in exc.reasons.values() if r]):
            return (
                "The travel assistant has run out of AI model quota on every "
                "configured provider (" + ", ".join(sorted(daily)) + "). "
                "It will be available again once the quota resets."
            )
        return (
            "The travel assistant cannot reach any AI model right now ("
            + "; ".join(f"{n}: {w}" for n, w in exc.reasons.items())
            + "). Please try again shortly."
        )
    if isinstance(exc, DailyQuotaExhausted) or is_daily_quota_exhausted(exc):
        return (
            "The travel assistant has reached its daily AI request limit, "
            "so it cannot answer right now. Please try again tomorrow."
        )
    return FALLBACK_ANSWER


def get_agent_response(
    query: str,
    chat_history: Sequence[tuple[str, str]] | None = None,
    image_data: bytes | None = None,
) -> dict[str, Any]:
    """
    Sync entry point used by the DRF view.

    Returns ``{"answer", "sources", "tools_used"}``. Safe to call from both
    WSGI (no running loop) and ASGI (loop already running).
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_arespond(query, chat_history, image_data))

    # Already inside an event loop: hand off to a worker thread that owns its
    # own loop rather than trying to nest one.
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(
            asyncio.run, _arespond(query, chat_history, image_data)
        ).result()


# Re-exported so callers that already speak async do not have to know the
# sync shim exists. ``_arespond`` is already a coroutine function, so it is
# aliased directly - wrapping it in ``async_to_sync`` would make the "async"
# entry point synchronous and emit a RuntimeWarning.
arespond = _arespond
get_agent_response_async = _arespond
