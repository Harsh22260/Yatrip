from django.db import models
from django.conf import settings
import secrets
import uuid

User = settings.AUTH_USER_MODEL


def generate_access_key() -> str:
    return secrets.token_urlsafe(32)


class ChatSession(models.Model):
    """One conversation session per user"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='chat_sessions',
        null=True, blank=True
    )
    # Secret the browser keeps alongside the session id. Sessions used to be
    # reachable by id alone, so anyone who learned a UUID could read another
    # person's chat history, append to it, or wipe it. Authenticated callers are
    # matched on `user`; this covers the anonymous case.
    access_key = models.CharField(max_length=64, default=generate_access_key, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Session {self.id} — {self.user}"

    def belongs_to(self, user) -> bool:
        """
        Whether an authenticated ``user`` owns this session.

        An anonymous session has no owner, so it never "belongs" to anyone; it
        is reachable only with the matching access key. Returning True for every
        anonymous caller here would make the key check dead code.
        """
        if self.user_id is None:
            return False
        return bool(getattr(user, "is_authenticated", False)) and self.user_id == user.id

    def is_accessible_to(self, user, key=None) -> bool:
        """Owner match, or possession of the session's access key."""
        return self.belongs_to(user) or self.key_matches(key)

    def key_matches(self, provided) -> bool:
        if not provided:
            return False
        return secrets.compare_digest(self.access_key, str(provided))

class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]

    session = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE,
        related_name='messages'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    image_url = models.TextField(null=True, blank=True) # Changed from ImageField to avoid Pillow dependency
    sources = models.JSONField(default=list, blank=True)   # RAG / tool sources
    tools_used = models.JSONField(default=list, blank=True) # agent tools
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.role}] {self.content[:60]}"