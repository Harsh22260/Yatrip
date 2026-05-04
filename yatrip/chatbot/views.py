import uuid
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import Conversation, Message
from .rag_engine import generate_response

User = get_user_model()


class ChatView(APIView):
    """
    POST /api/chatbot/chat/
    Body: { "message": "...", "conversation_id": (optional), "session_id": (optional) }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        user_message = request.data.get("message", "").strip()
        if not user_message:
            return Response(
                {"error": "Message cannot be empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Conversation fetch or create ───────────────────────────────────────
        conversation_id = request.data.get("conversation_id")
        session_id = request.data.get("session_id") or str(uuid.uuid4())

        if conversation_id:
            try:
                conversation = Conversation.objects.get(id=conversation_id)
            except Conversation.DoesNotExist:
                conversation = self._create_conversation(request, session_id)
        else:
            conversation = self._create_conversation(request, session_id)

        # ── Fetch last 6 messages for history ─────────────────────────────────
        recent_messages = conversation.messages.order_by("-created_at")[:6]
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in reversed(recent_messages)
        ]

        # ── Save user message ──────────────────────────────────────────────────
        Message.objects.create(
            conversation=conversation,
            role="user",
            content=user_message,
        )

        # ── Generate AI response ───────────────────────────────────────────────
        ai_response = generate_response(
            user_message=user_message,
            conversation_history=history,
            use_web_search=True,
        )

        # ── Save assistant message ─────────────────────────────────────────────
        Message.objects.create(
            conversation=conversation,
            role="assistant",
            content=ai_response,
        )

        return Response(
            {
                "response": ai_response,
                "conversation_id": conversation.id,
                "session_id": conversation.session_id,
            },
            status=status.HTTP_200_OK,
        )

    def _create_conversation(self, request, session_id):
        user = request.user if request.user.is_authenticated else None
        return Conversation.objects.create(user=user, session_id=session_id)


class ConversationHistoryView(APIView):
    """
    GET /api/chatbot/history/<conversation_id>/
    Ek conversation ki saari messages return karta hai
    """
    permission_classes = [AllowAny]

    def get(self, request, conversation_id):
        try:
            conversation = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response(
                {"error": "Conversation not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        messages = conversation.messages.all()
        data = [
            {
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in messages
        ]
        return Response({"messages": data}, status=status.HTTP_200_OK)


class ClearConversationView(APIView):
    """
    DELETE /api/chatbot/clear/<conversation_id>/
    """
    permission_classes = [AllowAny]

    def delete(self, request, conversation_id):
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            conversation.messages.all().delete()
            return Response({"message": "Conversation cleared."}, status=status.HTTP_200_OK)
        except Conversation.DoesNotExist:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
