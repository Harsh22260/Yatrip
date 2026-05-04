import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.shortcuts import get_object_or_404

from .models import ChatSession, ChatMessage
from .serializers import ChatMessageSerializer, ChatSessionSerializer

logger = logging.getLogger(__name__)


# ─── Helper: session ke messages se history banana ────────
def build_chat_history(session: ChatSession, limit: int = 10):
    """
    DB se last N message pairs fetch karo — LangChain format mein
    Returns: List of (human_msg, ai_msg) tuples
    """
    messages = session.messages.order_by('created_at')
    history = []
    user_msg = None

    for msg in messages:
        if msg.role == 'user':
            user_msg = msg.content
        elif msg.role == 'assistant' and user_msg:
            history.append((user_msg, msg.content))
            user_msg = None

    return history[-limit:]  # Last N pairs


# ─── CHAT VIEW ────────────────────────────────────────────
class ChatView(APIView):
    permission_classes = [permissions.AllowAny]  # TODO: change to IsAuthenticated after login fix

    def post(self, request):
        user_message = request.data.get("message", "").strip()
        session_id = request.data.get("session_id")

        if not user_message:
            return Response({"error": "Message required"}, status=400)

        if len(user_message) > 2000:
            return Response({"error": "Message too long (max 2000 chars)"}, status=400)

        # ── Session handle karo ──
        user = request.user if request.user.is_authenticated else None
        if session_id:
            try:
                session = ChatSession.objects.get(id=session_id)
            except ChatSession.DoesNotExist:
                session = ChatSession.objects.create(user=user)
        else:
            session = ChatSession.objects.create(user=user)

        # ── User message save karo ──
        ChatMessage.objects.create(
            session=session,
            role='user',
            content=user_message,
        )

        # ── Conversation history build karo ──
        chat_history = build_chat_history(session, limit=10)

        # ── RAG response lo ──
        try:
            from .rag_engine import get_rag_response  # lazy import
            result = get_rag_response(
                query=user_message,
                chat_history=chat_history,
            )
            reply = result["answer"]
            sources = result["sources"]
        except Exception as e:
            logger.error(f"RAG error in view: {e}")
            reply = "Sorry, kuch gadbad ho gayi. Thodi der baad try karo! 🙏"
            sources = []

        # ── Bot response save karo ──
        ChatMessage.objects.create(
            session=session,
            role='assistant',
            content=reply,
            sources=sources,
        )

        # ── Session update time ──
        session.save()

        return Response({
            "reply": reply,
            "session_id": str(session.id),
            "sources": sources,
        }, status=200)


# ─── HISTORY VIEW ─────────────────────────────────────────
class ChatHistoryView(APIView):
    """
    GET /api/chatbot/history/?session_id=<uuid>
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        session_id = request.query_params.get("session_id")
        if not session_id:
            # Return all sessions of user
            sessions = ChatSession.objects.filter(user=request.user).order_by('-updated_at')[:10]
            return Response(ChatSessionSerializer(sessions, many=True).data)

        session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        messages = session.messages.all()
        return Response({
            "session_id": str(session.id),
            "messages": ChatMessageSerializer(messages, many=True).data,
        })


# ─── CLEAR SESSION VIEW ───────────────────────────────────
class ClearSessionView(APIView):
    """
    POST /api/chatbot/clear/
    Body: { "session_id": "..." }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        session_id = request.data.get("session_id")
        if not session_id:
            return Response({"error": "session_id required"}, status=400)

        try:
            session = ChatSession.objects.get(id=session_id, user=request.user)
            session.messages.all().delete()
            return Response({"message": "Chat cleared successfully"})
        except ChatSession.DoesNotExist:
            return Response({"error": "Session not found"}, status=404)


# ─── SESSIONS LIST VIEW ───────────────────────────────────
class SessionsListView(APIView):
    """
    GET /api/chatbot/sessions/
    User ke saare sessions
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        sessions = ChatSession.objects.filter(user=request.user).order_by('-updated_at')[:20]
        data = []
        for s in sessions:
            last_msg = s.messages.filter(role='user').last()
            data.append({
                "session_id": str(s.id),
                "last_message": last_msg.content[:80] if last_msg else "New chat",
                "updated_at": s.updated_at,
                "message_count": s.messages.count(),
            })
        return Response(data)