
# chatbot_app/tasks.py
import os
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from celery import shared_task
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.models import User
from .models import ChatSession, ChatMessage, EmailVerification

@shared_task
def send_verification_email(user_id, token):
    """Send email verification after user signup"""
    try:
        user = User.objects.get(id=user_id)
        verification_url = f"http://localhost:8000/api/verify-email/{token}/"
        
        subject = "Please verify your email address"
        message = f"""
        Hello {user.username},
        
        Thank you for signing up for our AI Chatbot!
        
        Please click the following link to verify your email address:
        {verification_url}
        
        This link will expire in 24 hours.
        
        Best regards,
        AI Chatbot Team
        """
        
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )
        
        return f"Verification email sent to {user.email}"
        
    except Exception as e:
        return f"Failed to send verification email: {str(e)}"

@shared_task
def cleanup_old_chat_history():
    """Delete chat history older than 30 days - REQUIRED BY TASK"""
    try:
        cutoff_date = timezone.now() - timedelta(days=30)
        
        # Delete old messages
        old_messages = ChatMessage.objects.filter(timestamp__lt=cutoff_date)
        message_count = old_messages.count()
        old_messages.delete()
        
        # Delete empty sessions
        empty_sessions = ChatSession.objects.filter(
            messages__isnull=True,
            created_at__lt=cutoff_date
        )
        session_count = empty_sessions.count()
        empty_sessions.delete()
        
        return f"Cleaned up {message_count} messages and {session_count} empty sessions"
        
    except Exception as e:
        return f"Cleanup failed: {str(e)}"

@shared_task
def cleanup_expired_tokens():
    """Clean up expired email verification tokens"""
    try:
        expired_tokens = EmailVerification.objects.filter(
            expires_at__lt=timezone.now(),
            is_verified=False
        )
        count = expired_tokens.count()
        expired_tokens.delete()
        
        return f"Cleaned up {count} expired tokens"
        
    except Exception as e:
        return f"Token cleanup failed: {str(e)}"
