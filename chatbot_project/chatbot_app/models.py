# chatbot_app/models.py - ADD MISSING MODELS
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class ChatSession(models.Model):
    """Model to store chat sessions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Session {self.session_id} - {self.user.username if self.user else 'Anonymous'}"

    class Meta:
        ordering = ['-created_at']

class ChatMessage(models.Model):
    """Model to store individual chat messages"""
    MESSAGE_TYPES = [
        ('user', 'User'),
        ('bot', 'Bot'),
        ('system', 'System'),
    ]
    
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES)
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.message_type}: {self.content[:50]}..."

    class Meta:
        ordering = ['timestamp']

class UserPreference(models.Model):
    """Model to store user preferences for the chatbot"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    preferred_language = models.CharField(max_length=10, default='en')
    theme = models.CharField(max_length=20, default='light')
    chat_history_enabled = models.BooleanField(default=True)
    notifications_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Preferences for {self.user.username}"

class ChatbotConfig(models.Model):
    """Model to store chatbot configuration"""
    name = models.CharField(max_length=100, unique=True)
    model_name = models.CharField(max_length=100, default='llama2')
    system_prompt = models.TextField(default='You are a helpful assistant.')
    temperature = models.FloatField(default=0.7)
    max_tokens = models.IntegerField(default=1000)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']

# ADD THE MISSING MODELS THAT WERE CAUSING THE ERROR

class Document(models.Model):
    """Model to store documents for RAG pipeline"""
    title = models.CharField(max_length=200)
    content = models.TextField()
    document_type = models.CharField(max_length=50, default='text')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['-created_at']

class DocumentEmbedding(models.Model):
    """Model to store document embeddings for vector search"""
    document = models.OneToOneField(Document, on_delete=models.CASCADE)
    embedding_model = models.CharField(max_length=100)
    embedding_data = models.JSONField(default=list)  # Store as JSON array
    created_at = models.DateTimeField(default=timezone.now)
    
    def set_embedding(self, embedding_vector):
        """Store embedding vector as JSON"""
        if hasattr(embedding_vector, 'tolist'):
            self.embedding_data = embedding_vector.tolist()
        else:
            self.embedding_data = list(embedding_vector)
        
    def get_embedding(self):
        """Retrieve embedding vector"""
        return self.embedding_data
    
    def __str__(self):
        return f"Embedding for {self.document.title}"

class EmailVerification(models.Model):
    """Model to store email verification tokens"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    is_verified = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def __str__(self):
        return f"Verification for {self.user.username}"