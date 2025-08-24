# chatbot_app/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from . import views

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'sessions', views.ChatSessionViewSet, basename='chatsession')
router.register(r'documents', views.DocumentViewSet, basename='document')

urlpatterns = [
    # Home page
    path('', views.home, name='home'),
    
    # Authentication endpoints - REQUIRED BY TASK
    path('signup/', views.SignUpAPIView.as_view(), name='signup'),
    path('login/', views.LoginAPIView.as_view(), name='login'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Chat endpoints - REQUIRED BY TASK  
    path('chat/', views.ChatAPIView.as_view(), name='chat-api'),
    path('chat-history/', views.chat_history, name='chat-history'),
    path('simple-chat/', views.simple_chat, name='simple-chat'),
    
    # Other endpoints
    path('preferences/', views.user_preferences, name='user-preferences'),
    path('health/', views.health_check, name='health-check'),
    
    # Router URLs (sessions/, documents/)
    path('', include(router.urls)),
]