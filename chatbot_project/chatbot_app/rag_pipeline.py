import os
import json
import numpy as np
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import faiss
from django.conf import settings
from .models import Document, DocumentEmbedding

class RAGPipeline:
    """Retrieval-Augmented Generation Pipeline"""
    
    def __init__(self):
        self.embedding_model_name = getattr(settings, 'RAG_SETTINGS', {}).get(
            'EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2'
        )
        self.vector_dimension = getattr(settings, 'RAG_SETTINGS', {}).get(
            'VECTOR_DIMENSION', 384
        )
        self.top_k = getattr(settings, 'RAG_SETTINGS', {}).get(
            'TOP_K_RESULTS', 3
        )
        self.similarity_threshold = getattr(settings, 'RAG_SETTINGS', {}).get(
            'SIMILARITY_THRESHOLD', 0.7
        )
        
        self.embedding_model = None
        self.faiss_index = None
        self.document_mappings = {}
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize embedding model and FAISS index"""
        try:
            # Load embedding model
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            
            # Initialize FAISS index
            self.faiss_index = faiss.IndexFlatIP(self.vector_dimension)
            
            # Load existing embeddings
            self._load_existing_embeddings()
            
        except Exception as e:
            print(f"Error initializing RAG components: {e}")
    
    def _load_existing_embeddings(self):
        """Load existing document embeddings into FAISS index"""
        try:
            embeddings = DocumentEmbedding.objects.filter(
                document__is_active=True,
                embedding_model=self.embedding_model_name
            )
            
            if embeddings.exists():
                vectors = []
                doc_ids = []
                
                for embedding in embeddings:
                    vector = np.array(embedding.get_embedding(), dtype=np.float32)
                    vectors.append(vector)
                    doc_ids.append(embedding.document.id)
                
                if vectors:
                    vectors_array = np.array(vectors)
                    # Normalize vectors for cosine similarity
                    faiss.normalize_L2(vectors_array)
                    self.faiss_index.add(vectors_array)
                    
                    # Create document mapping
                    for i, doc_id in enumerate(doc_ids):
                        self.document_mappings[i] = doc_id
                        
        except Exception as e:
            print(f"Error loading embeddings: {e}")
    
    def add_document(self, document: Document) -> bool:
        """Add a new document to the RAG pipeline"""
        try:
            # Generate embedding for the document
            text_to_embed = f"{document.title}\n\n{document.content}"
            embedding_vector = self.embedding_model.encode([text_to_embed])[0]
            
            # Store embedding in database
            doc_embedding, created = DocumentEmbedding.objects.get_or_create(
                document=document,
                defaults={
                    'embedding_model': self.embedding_model_name
                }
            )
            doc_embedding.set_embedding(embedding_vector)
            doc_embedding.save()
            
            # Add to FAISS index
            vector = embedding_vector.astype(np.float32).reshape(1, -1)
            faiss.normalize_L2(vector)
            index_position = self.faiss_index.ntotal
            self.faiss_index.add(vector)
            self.document_mappings[index_position] = document.id
            
            return True
            
        except Exception as e:
            print(f"Error adding document to RAG: {e}")
            return False
    
    def retrieve_relevant_documents(self, query: str) -> List[Dict[str, Any]]:
        """Retrieve relevant documents for a given query"""
        try:
            if not self.embedding_model or self.faiss_index.ntotal == 0:
                return []
            
            # Generate query embedding
            query_vector = self.embedding_model.encode([query])[0]
            query_vector = query_vector.astype(np.float32).reshape(1, -1)
            faiss.normalize_L2(query_vector)
            
            # Search in FAISS index
            scores, indices = self.faiss_index.search(query_vector, self.top_k)
            
            relevant_docs = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if score >= self.similarity_threshold and idx in self.document_mappings:
                    doc_id = self.document_mappings[idx]
                    try:
                        document = Document.objects.get(id=doc_id, is_active=True)
                        relevant_docs.append({
                            'document': document,
                            'similarity_score': float(score),
                            'content': document.content,
                            'title': document.title
                        })
                    except Document.DoesNotExist:
                        continue
            
            return relevant_docs
            
        except Exception as e:
            print(f"Error retrieving documents: {e}")
            return []
    
    def generate_rag_context(self, query: str) -> str:
        """Generate context from retrieved documents"""
        relevant_docs = self.retrieve_relevant_documents(query)
        
        if not relevant_docs:
            return ""
        
        context_parts = []
        for doc in relevant_docs:
            context_parts.append(f"Document: {doc['title']}\nContent: {doc['content']}")
        
        return "\n\n---\n\n".join(context_parts)
    
    def rebuild_index(self):
        """Rebuild the entire FAISS index"""
        try:
            # Clear existing index
            self.faiss_index = faiss.IndexFlatIP(self.vector_dimension)
            self.document_mappings = {}
            
            # Reload embeddings
            self._load_existing_embeddings()
            
            return True
            
        except Exception as e:
            print(f"Error rebuilding index: {e}")
            return False
