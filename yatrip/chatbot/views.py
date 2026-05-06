import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.shortcuts import get_object_or_404
from datetime import datetime

from .models import ChatSession, ChatMessage
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


# ─── CHAT ─────────────────────────────────────────────────
class ChatView(APIView):
    """
    POST /api/chatbot/chat/
    Body: { "message": "...", "session_id": "uuid" (optional) }
    """
    permission_classes = [permissions.AllowAny]  # Change to IsAuthenticated after login fix

    def post(self, request):
        try:
            user_message = request.data.get("message", "").strip()
            session_id   = request.data.get("session_id")
            image_file   = request.FILES.get("image")

            if not user_message and not image_file:
                return Response({"error": "Message or image is required."}, status=400)

            # ── Session ──────────────────────────────────────
            user = request.user if request.user.is_authenticated else None
            if session_id:
                session = get_object_or_404(ChatSession, id=session_id)
            else:
                session = ChatSession.objects.create(user=user)

            # ── Save user message ─────────────────────────────
            # Using try-except for DB fields in case migrations weren't run
            try:
                user_msg_obj = ChatMessage.objects.create(
                    session=session, 
                    role='user', 
                    content=user_message or "Analyzed Image",
                    image_url=str(image_file) if image_file else None
                )
            except Exception as db_err:
                logger.warning(f"DB Error (likely missing migrations): {db_err}")
                # Fallback: create without image_url if field missing
                user_msg_obj = ChatMessage.objects.create(
                    session=session, 
                    role='user', 
                    content=user_message or "Analyzed Image"
                )

            # ── Build history ─────────────────────────────────
            history = build_chat_history(session)

            # ── Get Agent Response ────────────────────────────
            # Read image if exists
            img_bytes = None
            if image_file:
                try: image_file.seek(0); img_bytes = image_file.read()
                except: pass

            from .agent import get_agent_response  # lazy import
            agent_resp = get_agent_response(user_message, history, img_bytes)
            reply      = agent_resp.get("answer", "I'm sorry, I couldn't process that.")
            sources    = agent_resp.get("sources", [])
            tools_used = agent_resp.get("tools_used", [])

            # ── Save bot message ──────────────────────────────
            ChatMessage.objects.create(
                session=session,
                role='assistant',
                content=reply,
                sources=sources,
                tools_used=tools_used,
            )
            session.save()

            return Response({
                "reply":      reply,
                "session_id": str(session.id),
                "sources":    sources,
                "tools_used": tools_used,
                "image_url":  getattr(user_msg_obj, 'image_url', None)
            }, status=200)

        except Exception as e:
            logger.error(f"ChatView Error: {e}")
            return Response({
                "reply": "System busy. Please try again in a moment.",
                "error": str(e)
            }, status=500)


# ─── HISTORY ──────────────────────────────────────────────
class ChatHistoryView(APIView):
    """GET /api/chatbot/history/?session_id=<uuid>"""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        session_id = request.query_params.get("session_id")
        if not session_id:
            user = request.user if request.user.is_authenticated else None
            sessions = ChatSession.objects.filter(user=user).order_by('-updated_at')[:10]
            return Response(ChatSessionSerializer(sessions, many=True).data)

        session = get_object_or_404(ChatSession, id=session_id)
        return Response({
            "session_id": str(session.id),
            "messages":   ChatMessageSerializer(session.messages.all(), many=True).data,
        })


# ─── CLEAR ────────────────────────────────────────────────
class ClearSessionView(APIView):
    """POST /api/chatbot/clear/  Body: { "session_id": "..." }"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        session_id = request.data.get("session_id")
        if not session_id:
            return Response({"error": "session_id required."}, status=400)
        try:
            session = ChatSession.objects.get(id=session_id)
            session.messages.all().delete()
            return Response({"message": "Chat cleared successfully."})
        except ChatSession.DoesNotExist:
            return Response({"error": "Session not found."}, status=404)


# ─── SESSIONS LIST ─────────────────────────────────────────
class SessionsListView(APIView):
    """GET /api/chatbot/sessions/"""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            user = request.user if request.user.is_authenticated else None
            # If user is anonymous, we only show sessions that have no user (local storage based)
            # or if the user is logged in, show their sessions.
            sessions = ChatSession.objects.filter(user=user).order_by('-updated_at')[:20]
            data = []
            for s in sessions:
                try:
                    last = s.messages.filter(role='user').last()
                    data.append({
                        "session_id":    str(s.id),
                        "last_message":  last.content[:80] if (last and last.content) else "New chat",
                        "updated_at":    s.updated_at,
                        "message_count": s.messages.count(),
                    })
                except Exception as e:
                    logger.error(f"Error processing session {s.id}: {e}")
                    continue
            return Response(data)
        except Exception as e:
            logger.error(f"SessionsListView error: {e}")
            return Response({"error": str(e)}, status=500)