
# chatbot_app/apps.py - FIXED VERSION
from django.apps import AppConfig

class ChatbotAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chatbot_app'
    
    def ready(self):
        # Only import signals when the app is ready
        # Uncomment this when you have signals
        # try:
        #     import chatbot_app.signals
        # except ImportError:
        #     pass
        pass