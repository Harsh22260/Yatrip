from django.db import models
from pgvector.django import VectorField

class KnowledgeDocument(models.Model):
    """
    Ye model store karega hotels, food, attractions, etc. ka text data 
    + unka embedding vector (search ke liye).
    """
    source_type = models.CharField(max_length=50)   # hotel / food / rental / attraction
    title = models.CharField(max_length=255)
    content = models.TextField()
    embedding = VectorField(dimensions=384)         # 384 = MiniLM model embedding size
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.source_type})"