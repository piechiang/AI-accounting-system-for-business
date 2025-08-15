"""
Embedding service for transaction classification using local sentence transformers.
Provides semantic similarity matching for transaction descriptions.
"""

import numpy as np
from typing import List, Optional, Dict, Any, Tuple
import hashlib
import json
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session

# TODO: Replace with actual sentence-transformers when ready
# from sentence_transformers import SentenceTransformer
# import faiss

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Service for generating and comparing transaction embeddings."""
    
    def __init__(self, db: Session):
        self.db = db
        self.model = None
        self.index = None
        self.embeddings_cache = {}
        self.similarity_threshold = 0.85
        
        # TODO: Uncomment when sentence-transformers is available
        # self._initialize_model()
        
    def _initialize_model(self):
        """Initialize the sentence transformer model."""
        try:
            # TODO: Replace with actual model initialization
            # self.model = SentenceTransformer('all-MiniLM-L6-v2')
            # logger.info("Sentence transformer model loaded successfully")
            pass
        except Exception as e:
            logger.warning(f"Could not load sentence transformer model: {e}")
            self.model = None
    
    def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Generate embedding for text.
        
        Args:
            text: Input text to embed
            
        Returns:
            Embedding vector or None if model unavailable
        """
        if not self.model:
            # Placeholder implementation - returns dummy embedding
            # TODO: Replace with actual model.encode(text)
            return self._generate_dummy_embedding(text)
        
        try:
            # TODO: Uncomment when model is available
            # embedding = self.model.encode([text])
            # return embedding[0]
            return self._generate_dummy_embedding(text)
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    def _generate_dummy_embedding(self, text: str) -> np.ndarray:
        """
        Generate deterministic dummy embedding for testing.
        
        Args:
            text: Input text
            
        Returns:
            384-dimensional dummy embedding
        """
        # Create deterministic embedding based on text hash
        hash_obj = hashlib.md5(text.encode())
        hash_int = int(hash_obj.hexdigest(), 16)
        
        # Generate pseudo-random but deterministic 384-dim vector
        np.random.seed(hash_int % (2**32))
        embedding = np.random.normal(0, 1, 384)
        
        # Normalize to unit vector
        embedding = embedding / np.linalg.norm(embedding)
        
        return embedding
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score [0, 1]
        """
        try:
            # Cosine similarity
            dot_product = np.dot(embedding1, embedding2)
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
                
            similarity = dot_product / (norm1 * norm2)
            
            # Convert to [0, 1] range
            return (similarity + 1) / 2
        except Exception as e:
            logger.error(f"Error computing similarity: {e}")
            return 0.0
    
    def find_similar_transactions(
        self, 
        transaction_text: str, 
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find similar historical transactions using embeddings.
        
        Args:
            transaction_text: Text to match against
            top_k: Number of similar transactions to return
            
        Returns:
            List of similar transactions with similarity scores
        """
        query_embedding = self.get_embedding(transaction_text)
        if query_embedding is None:
            return []
        
        # TODO: Implement FAISS index search when available
        # For now, return placeholder results
        return self._find_similar_placeholder(transaction_text, top_k)
    
    def _find_similar_placeholder(self, transaction_text: str, top_k: int) -> List[Dict[str, Any]]:
        """
        Placeholder implementation for similarity search.
        
        Args:
            transaction_text: Query text
            top_k: Number of results
            
        Returns:
            Mock similarity results
        """
        # Generate mock similar transactions for testing
        mock_transactions = [
            {
                'transaction_id': 1,
                'description': f'Similar to: {transaction_text[:20]}...',
                'coa_code': '5100',
                'coa_name': 'Office Expenses',
                'similarity_score': 0.92,
                'confidence': 0.87
            },
            {
                'transaction_id': 2,
                'description': f'Related: {transaction_text[:15]}...',
                'coa_code': '5200',
                'coa_name': 'Travel Expenses',
                'similarity_score': 0.88,
                'confidence': 0.85
            }
        ]
        
        return mock_transactions[:top_k]
    
    def classify_by_embedding(
        self, 
        transaction_text: str, 
        amount: float = None
    ) -> Optional[Dict[str, Any]]:
        """
        Classify transaction using embedding similarity.
        
        Args:
            transaction_text: Transaction description to classify
            amount: Transaction amount (optional)
            
        Returns:
            Classification result or None if confidence too low
        """
        similar_transactions = self.find_similar_transactions(transaction_text, top_k=3)
        
        if not similar_transactions:
            return None
        
        # Use the most similar transaction if confidence is high enough
        best_match = similar_transactions[0]
        
        if best_match['similarity_score'] >= self.similarity_threshold:
            return {
                'predicted_coa_code': best_match['coa_code'],
                'predicted_coa_name': best_match['coa_name'],
                'confidence': best_match['confidence'],
                'similarity_score': best_match['similarity_score'],
                'source_transaction_id': best_match['transaction_id'],
                'method': 'embedding'
            }
        
        return None
    
    def build_embeddings_index(self, force_rebuild: bool = False):
        """
        Build or rebuild the embeddings index from historical transactions.
        
        Args:
            force_rebuild: Whether to force rebuild existing index
        """
        # TODO: Implement FAISS index building
        # 1. Query all historical transactions with classifications
        # 2. Generate embeddings for each transaction
        # 3. Build FAISS index for fast similarity search
        # 4. Save index to disk for persistence
        
        logger.info("Embeddings index building not yet implemented")
        pass
    
    def update_embeddings_cache(self, transaction_id: int, embedding: np.ndarray):
        """
        Update the embeddings cache with new transaction embedding.
        
        Args:
            transaction_id: ID of the transaction
            embedding: Embedding vector to cache
        """
        self.embeddings_cache[transaction_id] = {
            'embedding': embedding,
            'timestamp': datetime.now()
        }
        
        # Clean old cache entries (older than 1 hour)
        cutoff_time = datetime.now() - timedelta(hours=1)
        self.embeddings_cache = {
            k: v for k, v in self.embeddings_cache.items()
            if v['timestamp'] > cutoff_time
        }
    
    def get_cached_embedding(self, transaction_id: int) -> Optional[np.ndarray]:
        """
        Get cached embedding for a transaction.
        
        Args:
            transaction_id: ID of the transaction
            
        Returns:
            Cached embedding or None if not found/expired
        """
        if transaction_id in self.embeddings_cache:
            cache_entry = self.embeddings_cache[transaction_id]
            
            # Check if cache entry is still valid (1 hour TTL)
            if datetime.now() - cache_entry['timestamp'] < timedelta(hours=1):
                return cache_entry['embedding']
            else:
                # Remove expired entry
                del self.embeddings_cache[transaction_id]
        
        return None

# TODO: Installation instructions for when ready to implement:
# pip install sentence-transformers faiss-cpu
# 
# For cloud embedding alternatives, add these placeholder methods:
#
# def get_openai_embedding(self, text: str) -> Optional[np.ndarray]:
#     """Get embedding from OpenAI API."""
#     pass
#
# def get_cohere_embedding(self, text: str) -> Optional[np.ndarray]:
#     """Get embedding from Cohere API.""" 
#     pass
#
# def get_huggingface_embedding(self, text: str) -> Optional[np.ndarray]:
#     """Get embedding from HuggingFace Inference API."""
#     pass