# chatbot_app/management/commands/setup_rag.py
from django.core.management.base import BaseCommand
from django.conf import settings
from chatbot_app.models import Document
from chatbot_app.rag_pipeline import RAGPipeline
import os

class Command(BaseCommand):
    help = 'Setup RAG pipeline with sample documents'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sample-docs',
            action='store_true',
            help='Add sample documents for testing',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up RAG pipeline...'))
        
        # Initialize RAG pipeline
        rag_pipeline = RAGPipeline()
        
        if options['sample_docs']:
            self.add_sample_documents(rag_pipeline)
        
        self.stdout.write(self.style.SUCCESS('RAG pipeline setup completed!'))

    def add_sample_documents(self, rag_pipeline):
        """Add sample documents for testing"""
        sample_docs = [
            {
                'title': 'AI Chatbot FAQ',
                'content': """
                Q: What is this chatbot?
                A: This is an AI-powered chatbot that can answer questions and have conversations.
                
                Q: How does it work?
                A: The chatbot uses advanced language models and retrieval-augmented generation to provide accurate responses.
                
                Q: Can I save my conversation history?
                A: Yes, if you're logged in, your conversations are automatically saved.
                """
            },
            {
                'title': 'Technical Documentation',
                'content': """
                This chatbot is built using Django REST Framework with the following features:
                - JWT authentication for secure user sessions
                - RAG pipeline for enhanced responses using document retrieval
                - Chat history storage and management
                - Background tasks for maintenance
                - RESTful API endpoints for integration
                """
            },
            {
                'title': 'Getting Started Guide',
                'content': """
                To get started with the chatbot:
                1. Create an account using the signup endpoint
                2. Verify your email address
                3. Log in to get your JWT tokens
                4. Start chatting using the chat endpoint
                5. View your chat history anytime
                """
            }
        ]
        
        for doc_data in sample_docs:
            document, created = Document.objects.get_or_create(
                title=doc_data['title'],
                defaults={
                    'content': doc_data['content'],
                    'document_type': 'text',
                    'is_active': True
                }
            )
            
            if created:
                rag_pipeline.add_document(document)
                self.stdout.write(f'Added document: {document.title}')
            else:
                self.stdout.write(f'Document already exists: {document.title}')
