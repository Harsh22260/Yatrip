from django.urls import path
from .views import ChatView, ConversationHistoryView, ClearConversationView

urlpatterns = [
    path("chat/", ChatView.as_view(), name="chatbot-chat"),
    path("history/<int:conversation_id>/", ConversationHistoryView.as_view(), name="chatbot-history"),
    path("clear/<int:conversation_id>/", ClearConversationView.as_view(), name="chatbot-clear"),
]
