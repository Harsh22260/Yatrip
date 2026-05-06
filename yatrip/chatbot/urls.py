from django.urls import path
from .views import ChatView, ChatHistoryView, ClearSessionView, SessionsListView

urlpatterns = [
    path('chat/',     ChatView.as_view(),        name='chatbot-chat'),
    path('history/',  ChatHistoryView.as_view(),  name='chatbot-history'),
    path('clear/',    ClearSessionView.as_view(), name='chatbot-clear'),
    path('sessions/', SessionsListView.as_view(), name='chatbot-sessions'),
]