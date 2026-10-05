import logging

from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ChatMessage, ChatSession
from .serializers import ChatMessageSerializer, ChatSessionSerializer

logger = logging.getLogger(__name__)


def build_chat_history(session: ChatSession, limit: int = 8):
    """DB se last N message pairs — LangGraph format ke liye"""
    messages = list(session.messages.order_by('created_at'))
    history = []
    user_msg = None
    for msg in messages:
        if msg.role == 'user':
            user_msg = msg.content
        elif msg.role == 'assistant' and user_msg:
            history.append((user_msg, msg.content))
            user_msg = None
    return history[-limit:]


def get_owned_session(request, session_id, *, key=None) -> ChatSession:
    """
    Fetch a session the caller is actually allowed to touch.

    Previously every endpoint did ``get_object_or_404(ChatSession, id=...)`` with
    no ownership check, so any client that knew a session UUID could read the
    whole conversation, append messages to it, or delete it (IDOR). Authenticated
    callers are matched on ``user``; anonymous ones must present the session's
    ``access_key``.
    """
    session = get_object_or_404(ChatSession, id=session_id)
    if session.is_accessible_to(request.user, key=key):
        return session
    raise _Forbidden("You do not have access to this chat session.")


class _Forbidden(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


# ─── CHAT ─────────────────────────────────────────────────
class ChatView(APIView):
    """
    POST /api/chatbot/chat/
    Body: { "message": "...", "session_id": "uuid" (optional),
            "access_key": "..." (required to resume an anonymous session) }
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        user_message = (request.data.get("message") or "").strip()
        session_id = request.data.get("session_id")
        access_key = request.data.get("access_key")
        image_file = request.FILES.get("image")

        if not user_message and not image_file:
            return Response(
                {"error": "Message or image is required.", "code": "empty_message"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if session_id:
                session = get_owned_session(request, session_id, key=access_key)
            else:
                session = ChatSession.objects.create(
                    user=request.user if request.user.is_authenticated else None
                )
        except _Forbidden as exc:
            return Response(
                {"error": exc.message, "code": "forbidden"}, status=status.HTTP_403_FORBIDDEN
            )

        try:
            user_msg_obj = ChatMessage.objects.create(
                session=session,
                role='user',
                content=user_message or "Analyzed Image",
                image_url=str(image_file) if image_file else None,
            )
        except Exception:
            # Let a genuine database failure surface as a 500 with a real trace
            # instead of being swallowed and retried as if it were a missing
            # column, which hid real errors for a long time.
            logger.exception("Failed to store the user message for session %s", session.id)
            return Response(
                {"error": "Could not save your message. Please try again.", "code": "save_failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        history = build_chat_history(session)

        img_bytes = None
        if image_file is not None:
            try:
                image_file.seek(0)
                img_bytes = image_file.read()
            except Exception:
                logger.warning("Could not read the uploaded image", exc_info=True)
                img_bytes = None

        from .agent import get_agent_response  # lazy import

        try:
            agent_resp = get_agent_response(user_message, history, img_bytes)
        except Exception:
            # Previously str(e) was returned to the client, leaking internals.
            logger.exception("Agent failed for session %s", session.id)
            agent_resp = {
                "answer": "Something went wrong on my side. Please try again.",
                "sources": [],
                "tools_used": [],
            }

        reply = agent_resp.get("answer") or "I'm sorry, I couldn't process that."
        sources = agent_resp.get("sources") or []
        tools_used = agent_resp.get("tools_used") or []

        ChatMessage.objects.create(
            session=session,
            role='assistant',
            content=reply,
            sources=sources,
            tools_used=tools_used,
        )
        session.save()

        return Response(
            {
                "reply": reply,
                "session_id": str(session.id),
                # The browser must keep this to resume an anonymous session.
                "access_key": session.access_key,
                "sources": sources,
                "tools_used": tools_used,
                "image_url": user_msg_obj.image_url,
            },
            status=status.HTTP_200_OK,
        )


# ─── HISTORY ──────────────────────────────────────────────
class ChatHistoryView(APIView):
    """GET /api/chatbot/history/?session_id=<uuid>&access_key=<key>"""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        session_id = request.query_params.get("session_id")
        access_key = request.query_params.get("access_key")

        if not session_id:
            user = request.user if request.user.is_authenticated else None
            sessions = ChatSession.objects.filter(user=user).order_by('-updated_at')[:10]
            return Response(ChatSessionSerializer(sessions, many=True).data)

        try:
            session = get_owned_session(request, session_id, key=access_key)
        except _Forbidden as exc:
            return Response(
                {"error": exc.message, "code": "forbidden"}, status=status.HTTP_403_FORBIDDEN
            )

        return Response(
            {
                "session_id": str(session.id),
                "messages": ChatMessageSerializer(session.messages.all(), many=True).data,
            }
        )


# ─── CLEAR ────────────────────────────────────────────────
class ClearSessionView(APIView):
    """POST /api/chatbot/clear/  Body: { "session_id": "...", "access_key": "..." }"""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        session_id = request.data.get("session_id")
        if not session_id:
            return Response({"error": "session_id required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = get_owned_session(request, session_id, key=request.data.get("access_key"))
        except _Forbidden as exc:
            return Response(
                {"error": exc.message, "code": "forbidden"}, status=status.HTTP_403_FORBIDDEN
            )

        session.messages.all().delete()
        return Response({"message": "Chat cleared successfully."})


# ─── SESSIONS LIST ─────────────────────────────────────────
class SessionsListView(APIView):
    """GET /api/chatbot/sessions/"""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        user = request.user if request.user.is_authenticated else None
        sessions = ChatSession.objects.filter(user=user).order_by('-updated_at')[:20]
        data = []
        for s in sessions:
            last = s.messages.filter(role='user').last()
            data.append(
                {
                    "session_id": str(s.id),
                    "last_message": last.content[:80] if (last and last.content) else "New chat",
                    "updated_at": s.updated_at,
                    "message_count": s.messages.count(),
                }
            )
        return Response(data)
