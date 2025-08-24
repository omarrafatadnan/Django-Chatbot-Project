# chatbot_app/serializers.py - COMPLETE VERSION with all missing serializers

from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from .models import (
    ChatSession, ChatMessage, UserPreference,
    ChatbotConfig, Document, EmailVerification
)

# Try to import optional models (they might not exist yet)
try:
    from .models import Document, EmailVerification
    DOCUMENT_MODEL_AVAILABLE = True
except ImportError:
    DOCUMENT_MODEL_AVAILABLE = False


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'first_name', 'last_name']

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            data['user'] = user
        else:
            raise serializers.ValidationError('Must include username and password')
        return data


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'message_type', 'content', 'timestamp', 'metadata']
        read_only_fields = ['id', 'timestamp']


class ChatSessionSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = ['id', 'session_id', 'created_at', 'updated_at', 'is_active', 'messages', 'message_count']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_message_count(self, obj):
        return obj.messages.count()


# MISSING SERIALIZER - This was causing the error
class UserPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreference
        fields = ['preferred_language', 'theme', 'chat_history_enabled', 
                 'notifications_enabled', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000)
    session_id = serializers.CharField(max_length=100, required=False)
    use_rag = serializers.BooleanField(default=True)


class ChatbotConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatbotConfig
        fields = ['id', 'name', 'model_name', 'system_prompt', 'temperature', 
                 'max_tokens', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


# Optional serializers (only if models exist)
if DOCUMENT_MODEL_AVAILABLE:
    class DocumentSerializer(serializers.ModelSerializer):
        class Meta:
            model = Document
            fields = ['id', 'title', 'content', 'document_type', 'created_at', 'is_active']
    
    class EmailVerificationSerializer(serializers.ModelSerializer):
        class Meta:
            model = EmailVerification
            fields = ['token', 'created_at', 'expires_at', 'is_verified']
            read_only_fields = ['created_at', 'expires_at']
else:
    # Placeholder serializers if models don't exist
    class DocumentSerializer(serializers.Serializer):
        id = serializers.IntegerField(read_only=True)
        title = serializers.CharField(max_length=200)
        content = serializers.CharField()
        document_type = serializers.CharField(max_length=50, default='text')
        created_at = serializers.DateTimeField(read_only=True)
        is_active = serializers.BooleanField(default=True)