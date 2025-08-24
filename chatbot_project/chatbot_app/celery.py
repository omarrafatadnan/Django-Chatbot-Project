# chatbot_project/celery.py - FIXED VERSION
import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_project.settings')

app = Celery('chatbot_project')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# MOVE THE SCHEDULE CONFIGURATION INSIDE A FUNCTION OR REMOVE FOR NOW
# Comment out the beat_schedule until Django is properly set up

# Schedule periodic tasks - COMMENTED OUT TO FIX STARTUP ISSUE
"""
from celery.schedules import crontab
app.conf.beat_schedule = {
    'cleanup-old-chat-history': {
        'task': 'chatbot_app.tasks.cleanup_old_chat_history',
        'schedule': crontab(hour=2, minute=0),  # Run daily at 2 AM
    },
    'cleanup-expired-tokens': {
        'task': 'chatbot_app.tasks.cleanup_expired_tokens',
        'schedule': crontab(hour=3, minute=0),  # Run daily at 3 AM
    },
}
"""

app.conf.timezone = 'UTC'