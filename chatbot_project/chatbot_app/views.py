# chatbot_app/views.py - Fixed imports section

import json
import uuid
import requests
from datetime import datetime, timedelta
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

# Import your models
from .models import (
    ChatSession, ChatMessage, UserPreference, ChatbotConfig
)

# Import serializers with error handling
try:
    from .serializers import (
        UserRegistrationSerializer, UserLoginSerializer,
        ChatSessionSerializer, ChatMessageSerializer,
        UserPreferenceSerializer, ChatRequestSerializer,
        UserSerializer, DocumentSerializer
    )
    SERIALIZERS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some serializers not available: {e}")
    SERIALIZERS_AVAILABLE = False
    # Create minimal fallback serializers if needed
    from rest_framework import serializers
    
    class UserPreferenceSerializer(serializers.ModelSerializer):
        class Meta:
            model = UserPreference
            fields = '__all__'


def home(request):
    """Home page view"""
    return render(request, 'chatbot_app/index.html')


# JWT AUTHENTICATION VIEWS
class SignUpAPIView(APIView):
    """User registration endpoint"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        if not SERIALIZERS_AVAILABLE:
            return Response({'error': 'Serializers not properly configured'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Create user preferences
            UserPreference.objects.get_or_create(user=user)
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            return Response({
                'message': 'User created successfully.',
                'user': UserSerializer(user).data,
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh)
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginAPIView(APIView):
    """User login endpoint"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        if not SERIALIZERS_AVAILABLE:
            return Response({'error': 'Serializers not properly configured'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            return Response({
                'message': 'Login successful',
                'user': UserSerializer(user).data,
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh)
                }
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChatbotService:
    """Simplified chatbot service"""
    
    def __init__(self):
        self.base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
        self.default_model = getattr(settings, 'OLLAMA_MODEL', 'llama2')
    
    def generate_response(self, message, model_name=None, system_prompt=None):
        """Generate response from Ollama or fallback"""
        try:
            model = model_name or self.default_model
            payload = {
                "model": model,
                "prompt": message,
                "stream": False
            }
            if system_prompt:
                payload["system"] = system_prompt
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'response': data.get('response', ''),
                    'model': model,
                    'tokens': data.get('eval_count', 0)
                }
            else:
                return {
                    'success': False,
                    'error': f'Ollama API error: {response.status_code}'
                }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Connection error: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }
    
    def get_fallback_response(self, message):
        """Intelligent fallback responses when AI is not available"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['hello', 'hi', 'hey']):
            return "Hello! How can I help you today?"
        elif any(word in message_lower for word in ['how are you']):
            return "I'm doing well, thank you for asking! How can I assist you?"
        elif any(word in message_lower for word in ['thank', 'thanks']):
            return "You're welcome! Is there anything else I can help you with?"
        elif any(word in message_lower for word in ['bye', 'goodbye']):
            return "Goodbye! Have a great day!"
        elif any(word in message_lower for word in ['help', 'support']):
            return "I'm here to help! You can ask me questions about various topics."
        else:
            return "That's an interesting question! I'm currently running in basic mode, but I'm here to assist you as best I can."


class ChatAPIView(APIView):
    """Chat API endpoint"""
    permission_classes = [AllowAny]
    
    def __init__(self):
        super().__init__()
        self.chatbot_service = ChatbotService()
    
    def post(self, request):
        # Basic validation without serializer if needed
        data = request.data
        message = data.get('message', '').strip()
        
        if not message:
            return Response({'error': 'Message is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if len(message) > 2000:
            return Response({'error': 'Message too long'}, status=status.HTTP_400_BAD_REQUEST)
        
        session_id = data.get('session_id') or str(uuid.uuid4())
        
        # Get or create chat session
        session, created = ChatSession.objects.get_or_create(
            session_id=session_id,
            defaults={
                'user': request.user if request.user.is_authenticated else None,
                'is_active': True
            }
        )
        
        # Save user message
        user_message = ChatMessage.objects.create(
            session=session,
            message_type='user',
            content=message
        )
        
        # Get chatbot configuration
        try:
            config = ChatbotConfig.objects.filter(is_active=True).first()
            system_prompt = config.system_prompt if config else None
            model_to_use = config.model_name if config else None
        except:
            config = None
            system_prompt = None
            model_to_use = None
        
        # Generate response
        result = self.chatbot_service.generate_response(
            message=message,
            model_name=model_to_use,
            system_prompt=system_prompt
        )
        
        if result['success']:
            bot_response = result['response']
            metadata = {
                'model_used': result['model'],
                'tokens_used': result.get('tokens', 0),
                'ai_available': True
            }
        else:
            bot_response = self.chatbot_service.get_fallback_response(message)
            metadata = {
                'error': result['error'],
                'fallback_used': True,
                'ai_available': False
            }
        
        # Save bot message
        bot_message = ChatMessage.objects.create(
            session=session,
            message_type='bot',
            content=bot_response,
            metadata=metadata
        )
        
        # Update session timestamp
        session.updated_at = timezone.now()
        session.save()
        
        # Prepare response
        response_data = {
            'response': bot_response,
            'session_id': session_id,
            'timestamp': bot_message.timestamp.isoformat(),
            'model_used': metadata.get('model_used', 'fallback'),
            'ai_available': metadata.get('ai_available', False)
        }
        
        if metadata.get('tokens_used'):
            response_data['tokens_used'] = metadata['tokens_used']
        
        return Response(response_data, status=status.HTTP_200_OK)


# CHAT HISTORY ENDPOINT
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chat_history(request):
    """Get chat history for authenticated user"""
    try:
        sessions = ChatSession.objects.filter(
            user=request.user,
            is_active=True
        ).prefetch_related('messages').order_by('-updated_at')[:20]
        
        if SERIALIZERS_AVAILABLE:
            serializer = ChatSessionSerializer(sessions, many=True)
            return Response({
                'sessions': serializer.data,
                'total_sessions': sessions.count()
            })
        else:
            # Fallback without serializer
            sessions_data = []
            for session in sessions:
                sessions_data.append({
                    'id': session.id,
                    'session_id': session.session_id,
                    'created_at': session.created_at.isoformat(),
                    'updated_at': session.updated_at.isoformat(),
                    'message_count': session.messages.count()
                })
            return Response({
                'sessions': sessions_data,
                'total_sessions': sessions.count()
            })
    except Exception as e:
        return Response(
            {'error': f'Failed to retrieve chat history: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class ChatSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing chat sessions"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return ChatSession.objects.filter(user=self.request.user).order_by('-updated_at')
    
    def get_serializer_class(self):
        if SERIALIZERS_AVAILABLE:
            return ChatSessionSerializer
        else:
            # Return a basic serializer
            from rest_framework import serializers
            class BasicChatSessionSerializer(serializers.ModelSerializer):
                class Meta:
                    model = ChatSession
                    fields = '__all__'
            return BasicChatSessionSerializer


# Add missing DocumentViewSet
class DocumentViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for documents (placeholder)"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Return empty queryset for now since Document model might not exist
        from django.db import models
        return models.QuerySet().none()
    
    def get_serializer_class(self):
        if SERIALIZERS_AVAILABLE:
            return DocumentSerializer
        else:
            from rest_framework import serializers
            class PlaceholderSerializer(serializers.Serializer):
                id = serializers.IntegerField()
                title = serializers.CharField()
            return PlaceholderSerializer


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def user_preferences(request):
    """API endpoint for user preferences"""
    try:
        preference, created = UserPreference.objects.get_or_create(
            user=request.user
        )
    except:
        return Response({'error': 'Unable to access preferences'},
                      status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    if request.method == 'GET':
        if SERIALIZERS_AVAILABLE:
            serializer = UserPreferenceSerializer(preference)
            return Response(serializer.data)
        else:
            # Manual serialization
            return Response({
                'preferred_language': preference.preferred_language,
                'theme': preference.theme,
                'chat_history_enabled': preference.chat_history_enabled,
                'notifications_enabled': preference.notifications_enabled
            })
    
    elif request.method == 'POST':
        if SERIALIZERS_AVAILABLE:
            serializer = UserPreferenceSerializer(preference, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Manual update
            data = request.data
            if 'preferred_language' in data:
                preference.preferred_language = data['preferred_language']
            if 'theme' in data:
                preference.theme = data['theme']
            if 'chat_history_enabled' in data:
                preference.chat_history_enabled = data['chat_history_enabled']
            if 'notifications_enabled' in data:
                preference.notifications_enabled = data['notifications_enabled']
            preference.save()
            return Response({'message': 'Preferences updated'})


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint"""
    try:
        session_count = ChatSession.objects.count()
        
        # Test Ollama connection
        chatbot_service = ChatbotService()
        try:
            ollama_status = requests.get(f"{chatbot_service.base_url}/api/tags", timeout=3)
            ollama_available = ollama_status.status_code == 200
            ollama_models = ollama_status.json() if ollama_available else []
        except:
            ollama_available = False
            ollama_models = []
        
        return Response({
            'status': 'healthy',
            'database': 'connected',
            'total_sessions': session_count,
            'ollama': {
                'available': ollama_available,
                'models': ollama_models
            },
            'serializers_available': SERIALIZERS_AVAILABLE,
            'timestamp': timezone.now()
        })
    except Exception as e:
        return Response({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': timezone.now()
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@csrf_exempt
@require_http_methods(["POST"])
def simple_chat(request):
    """Simple chat endpoint for basic interactions"""
    try:
        data = json.loads(request.body)
        message = data.get('message', '')
        
        if not message:
            return JsonResponse({'error': 'Message is required'}, status=400)
        
        chatbot_service = ChatbotService()
        result = chatbot_service.generate_response(message)
        
        if result['success']:
            return JsonResponse({
                'response': result['response'],
                'status': 'success',
                'model_used': result['model']
            })
        else:
            fallback = chatbot_service.get_fallback_response(message)
            return JsonResponse({
                'response': fallback,
                'status': 'fallback',
                'error': result['error'],
                'ai_available': False
            })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)