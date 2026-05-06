"""
Yatrip AI Agent — LangGraph + Gemini 2.0 Flash + Multi-Tool
============================================================
Tools:
1. web_search        — Tavily (real-time internet)
2. osm_search        — OpenStreetMap Nominatim (locations)
3. get_nearby_places — OSM Overpass API (nearby places)
4. get_weather       — Open-Meteo (free, no key needed)
5. yatrip_db_search  — Pinecone RAG (Yatrip local database)
"""

import os
import logging
import requests
from typing import Annotated, TypedDict
from datetime import datetime

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# 🛠️  TOOLS
# ═══════════════════════════════════════════════════════════

@tool
def web_search(query: str) -> str:
    """
    Search the internet for real-time information using Tavily.
    Use for: hotel reviews, travel tips, current prices, latest news,
    tourist info, anything needing up-to-date data from the web.
    """
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY", ""))
        results = client.search(
            query=query,
            max_results=5,
            search_depth="basic",
            include_answer=True,
        )
        output = ""
        if results.get("answer"):
            output += f"**Summary:** {results['answer']}\n\n"

        for r in results.get("results", [])[:4]:
            output += f"• **{r.get('title', '')}**: {r.get('content', '')[:250]}\n"

        return output.strip() or "No results found."
    except Exception as e:
        logger.error(f"web_search error: {e}")
        return f"Web search failed: {str(e)}"


@tool
def osm_search(place_name: str, city: str = "") -> str:
    """
    Search OpenStreetMap Nominatim for places, addresses, landmarks, coordinates.
    Use for: finding exact locations, addresses of hotels/restaurants/attractions.
    Args:
        place_name: Name of the place
        city: City name for better accuracy (optional)
    """
    try:
        query = f"{place_name} {city}".strip()
        res = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 5, "addressdetails": 1},
            headers={"User-Agent": "YatripAI/1.0"},
            timeout=8,
        )
        data = res.json()
        if not data:
            return f"No location found for '{query}' on OpenStreetMap."

        results = []
        for p in data[:3]:
            addr = p.get("address", {})
            results.append(
                f"📍 {p.get('display_name', '')}\n"
                f"   Type: {p.get('type', 'N/A')} | "
                f"Lat: {p.get('lat')}, Lon: {p.get('lon')}\n"
                f"   City: {addr.get('city', addr.get('town', 'N/A'))} | "
                f"State: {addr.get('state', 'N/A')}"
            )
        return "\n\n".join(results)
    except Exception as e:
        logger.error(f"osm_search error: {e}")
        return f"OSM search failed: {str(e)}"


@tool
def get_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "tourism",
    radius_meters: int = 1000,
) -> str:
    """
    Find nearby places using OpenStreetMap Overpass API.
    Use for: finding restaurants, hotels, attractions, bus stops near a location.
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        place_type: 'restaurant', 'hotel', 'attraction', 'bus_stop', 'metro', 'museum', 'park', 'cafe'
        radius_meters: Search radius in meters (default 1000)
    """
    try:
        tag_map = {
            "restaurant":  'amenity"="restaurant',
            "hotel":       'tourism"="hotel',
            "attraction":  'tourism"="attraction',
            "bus_stop":    'highway"="bus_stop',
            "metro":       'railway"="station',
            "museum":      'tourism"="museum',
            "park":        'leisure"="park',
            "cafe":        'amenity"="cafe',
            "temple":      'amenity"="place_of_worship',
        }
        tag = tag_map.get(place_type, 'tourism"="attraction')
        query = f"""
        [out:json][timeout:15];
        node["{tag}](around:{radius_meters},{latitude},{longitude});
        out body 8;
        """
        res = requests.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": query},
            timeout=15,
        )
        elements = res.json().get("elements", [])
        if not elements:
            return f"No {place_type}s found within {radius_meters}m."

        results = []
        for el in elements[:6]:
            tags = el.get("tags", {})
            name = tags.get("name", tags.get("name:en", "Unnamed"))
            info = f"📍 {name} ({el.get('lat')}, {el.get('lon')})"
            if tags.get("cuisine"):   info += f" | Cuisine: {tags['cuisine']}"
            if tags.get("opening_hours"): info += f" | Hours: {tags['opening_hours']}"
            if tags.get("phone"):     info += f" | ☎ {tags['phone']}"
            results.append(info)

        return f"Nearby {place_type}s:\n" + "\n".join(results)
    except Exception as e:
        logger.error(f"get_nearby_places error: {e}")
        return f"Nearby search failed: {str(e)}"


@tool
def get_weather(city: str) -> str:
    """
    Get current weather and 3-day forecast. Completely free, no API key needed.
    Use when user asks about weather before traveling to a city.
    Args:
        city: City name e.g. 'Delhi', 'Mumbai', 'Jaipur'
    """
    try:
        geo = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": city + " India", "format": "json", "limit": 1},
            headers={"User-Agent": "YatripAI/1.0"},
            timeout=5,
        ).json()
        if not geo:
            return f"Could not find coordinates for {city}."

        lat, lon = geo[0]["lat"], geo[0]["lon"]
        w = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat, "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "Asia/Kolkata",
                "forecast_days": 3,
            },
            timeout=8,
        ).json()

        cur = w.get("current", {})
        daily = w.get("daily", {})
        codes = {
            0: "Clear ☀️", 1: "Mainly clear 🌤️", 2: "Partly cloudy ⛅",
            3: "Overcast ☁️", 45: "Foggy 🌫️", 51: "Light drizzle 🌦️",
            61: "Rain 🌧️", 80: "Showers 🌦️", 95: "Thunderstorm ⛈️",
        }
        condition = codes.get(cur.get("weather_code", 0), "Unknown")

        result = (
            f"🌤️ **{city} Weather:**\n"
            f"Now: {cur.get('temperature_2m')}°C, {condition}\n"
            f"Humidity: {cur.get('relative_humidity_2m')}% | Wind: {cur.get('wind_speed_10m')} km/h\n\n"
            f"📅 3-Day Forecast:\n"
        )
        for i in range(min(3, len(daily.get("time", [])))):
            result += (
                f"  {daily['time'][i]}: "
                f"{daily['temperature_2m_max'][i]}°C / {daily['temperature_2m_min'][i]}°C"
                f" | Rain: {daily['precipitation_sum'][i]}mm\n"
            )
        return result
    except Exception as e:
        logger.error(f"get_weather error: {e}")
        return f"Weather unavailable: {str(e)}"


@tool
def yatrip_db_search(query: str) -> str:
    """
    Search Yatrip's verified local database (hotels, food, attractions, rentals).
    Use for: finding specific Yatrip listings and verified local data.
    """
    try:
        # Check if Pinecone is configured
        if not os.environ.get("PINECONE_API_KEY") or not os.environ.get("GEMINI_API_KEY"):
            return "Note: Yatrip RAG database is not connected (Missing API Keys). Providing general info instead."

        from langchain_pinecone import PineconeVectorStore
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=os.environ.get("GEMINI_API_KEY"),
        )
        vs = PineconeVectorStore(
            index_name=os.environ.get("PINECONE_INDEX_NAME", "yatrip-rag"),
            embedding=embeddings,
            pinecone_api_key=os.environ.get("PINECONE_API_KEY"),
        )
        docs = vs.similarity_search(query, k=4)
        if not docs:
            return "No matching data in Yatrip database for this specific query."

        results = []
        for doc in docs:
            src = doc.metadata.get("source", "yatrip").upper()
            title = doc.metadata.get("title", "Listing")
            results.append(f"[{src}] {title}\n{doc.page_content[:400]}")
        return "Verified Yatrip Data:\n\n" + "\n\n---\n\n".join(results)
    except Exception as e:
        logger.error(f"yatrip_db_search error: {e}")
        return "Note: Local database search is currently unavailable. Using web search instead."


# ═══════════════════════════════════════════════════════════
# 🤖  LANGGRAPH AGENT
# ═══════════════════════════════════════════════════════════

TOOLS = [web_search, osm_search, get_nearby_places, get_weather, yatrip_db_search]

SYSTEM_PROMPT = f"""You are Yatrip AI, an advanced Travel Agent for India.

Core Logic (Follow strictly):
1. **Source Hierarchy**: 
   - First, search Yatrip's local database using `yatrip_db_search`. 
   - If no specific results found, use `web_search` or other tools.
   - If tools fail or provide no data, do NOT show an error. Use your own knowledge to generate a similar, helpful travel response.
2. **Language Adherence**: You MUST respond in the EXACT same language as the user (Hindi/Hinglish/English).
3. **Capabilities**: 
   - Use `osm_search` and `get_nearby_places` for maps/locations.
   - Always show prices in ₹ (Indian Rupees).
4. **Resilience**: If a tool returns an error, ignore the error and answer based on your internal training data.
5. **Today's Date**: {datetime.now().strftime("%d %B %Y")}
"""


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def get_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=os.environ.get("GEMINI_API_KEY", ""),
        temperature=0.7,
    )


def should_continue(state: AgentState):
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END


def call_model(state: AgentState):
    llm = get_llm().bind_tools(TOOLS)
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    return {"messages": [llm.invoke(messages)]}


def build_agent():
    tool_node = ToolNode(TOOLS)
    g = StateGraph(AgentState)
    g.add_node("agent", call_model)
    g.add_node("tools", tool_node)
    g.set_entry_point("agent")
    g.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    g.add_edge("tools", "agent")
    return g.compile()


# ═══════════════════════════════════════════════════════════
# 🚀  MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════

def get_agent_response(query: str, chat_history: list = None, image_data: bytes = None) -> dict:
    """
    Args:
        query: User message
        chat_history: List of (human, ai) tuples
        image_data: Optional image bytes for vision analysis
    Returns:
        { answer, sources, tools_used }
    """
    try:
        agent = build_agent()
        llm = get_llm()

        # ── Vision Handling ──────────────────────────────
        if image_data:
            from langchain_core.messages import HumanMessage
            import base64
            
            image_part = {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(image_data).decode()}"},
            }
            content = [{"type": "text", "text": f"Analyze this image in context of travel/tourism and answer: {query}"}, image_part]
            
            messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=content)]
            resp = llm.invoke(messages)
            return {"answer": resp.content, "sources": ["🖼️ Image Analysis"], "tools_used": ["vision"]}

        # ── Regular Agent Flow ────────────────────────────
        messages = []
        if chat_history:
            for h, a in chat_history[-10:]:
                messages.append(HumanMessage(content=h))
                messages.append(AIMessage(content=a))
        messages.append(HumanMessage(content=query))

        result = agent.invoke({"messages": messages})

        # Final answer
        final = result["messages"][-1]
        answer = final.content if hasattr(final, "content") else str(final)

        # Tools used
        tools_used = []
        for msg in result["messages"]:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    name = tc.get("name", "")
                    if name and name not in tools_used:
                        tools_used.append(name)

        # Sources display name mapping
        source_map = {
            "web_search":        "🌐 Web Search",
            "osm_search":        "🗺️ OpenStreetMap",
            "get_nearby_places": "📍 OSM Nearby",
            "get_weather":       "🌤️ Weather API",
            "yatrip_db_search":  "🏨 Yatrip DB RAG",
        }
        sources = [source_map[t] for t in tools_used if t in source_map]

        return {"answer": answer, "sources": sources, "tools_used": tools_used}

    except Exception as e:
        logger.error(f"Agent error: {e}")
        try:
            fallback_llm = get_llm()
            resp = fallback_llm.invoke([SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=query)])
            return {"answer": resp.content, "sources": [], "tools_used": []}
        except Exception as e2:
            logger.error(f"Fallback error: {e2}")
            return {
                "answer": "Sorry, I'm experiencing some technical difficulties. Please try again later!",
                "sources": [], "tools_used": [],
            }