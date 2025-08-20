"""
Local embedding service using sentence-transformers
Replaces external embedding APIs with local models
"""

import asyncio
import logging
import os
import time
from typing import List, Optional, Dict, Any, Union
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from sentence_transformers import SentenceTransformer
import torch
from utils.logger import logger
from utils.config import config

class EmbeddingService:
    """Local embedding service using sentence-transformers"""
    
    # Default models for different use cases
    DEFAULT_MODELS = {
        'general': 'all-MiniLM-L6-v2',  # Fast, good general purpose
        'multilingual': 'paraphrase-multilingual-MiniLM-L12-v2',  # Multilingual support
        'code': 'microsoft/codebert-base',  # Better for code
        'large': 'all-mpnet-base-v2',  # Higher quality, slower
    }
    
    def __init__(self, model_name: Optional[str] = None, device: Optional[str] = None):
        self.model_name = model_name or self.DEFAULT_MODELS['general']
        self.device = device or self._get_best_device()
        self.model: Optional[SentenceTransformer] = None
        self.executor = ThreadPoolExecutor(max_workers=2)  # Limit concurrent embedding tasks
        self._model_cache: Dict[str, SentenceTransformer] = {}
        self._load_lock = asyncio.Lock()
        
        logger.info(f"Initializing embedding service with model: {self.model_name}, device: {self.device}")
    
    def _get_best_device(self) -> str:
        """Determine the best device for inference"""
        if torch.cuda.is_available():
            return 'cuda'
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return 'mps'  # Apple Silicon
        else:
            return 'cpu'
    
    async def initialize(self):
        """Initialize the embedding model"""
        async with self._load_lock:
            if self.model is None:
                await self._load_model(self.model_name)
    
    async def _load_model(self, model_name: str):
        """Load a sentence transformer model"""
        try:
            if model_name in self._model_cache:
                self.model = self._model_cache[model_name]
                return
            
            logger.info(f"Loading embedding model: {model_name}")
            start_time = time.time()
            
            # Load model in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            model = await loop.run_in_executor(
                self.executor,
                self._load_model_sync,
                model_name
            )
            
            self._model_cache[model_name] = model
            self.model = model
            
            load_time = time.time() - start_time
            logger.info(f"Model {model_name} loaded successfully in {load_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Failed to load embedding model {model_name}: {e}")
            raise
    
    def _load_model_sync(self, model_name: str) -> SentenceTransformer:
        """Synchronous model loading"""
        try:
            model = SentenceTransformer(model_name, device=self.device)
            
            # Optimize for inference
            model.eval()
            if hasattr(model, 'half') and self.device == 'cuda':
                model.half()  # Use half precision on GPU for speed
            
            return model
        except Exception as e:
            logger.error(f"Error in synchronous model loading: {e}")
            raise
    
    async def encode_text(
        self, 
        texts: Union[str, List[str]], 
        batch_size: int = 32,
        normalize_embeddings: bool = True,
        show_progress: bool = False
    ) -> Union[np.ndarray, List[np.ndarray]]:
        """
        Encode text(s) into embeddings
        
        Args:
            texts: Single text string or list of texts
            batch_size: Batch size for processing
            normalize_embeddings: Whether to normalize embeddings
            show_progress: Whether to show progress bar
            
        Returns:
            Numpy array of embeddings
        """
        if not self.model:
            await self.initialize()
        
        is_single = isinstance(texts, str)
        if is_single:
            texts = [texts]
        
        try:
            start_time = time.time()
            
            # Run encoding in thread pool
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                self.executor,
                self._encode_sync,
                texts,
                batch_size,
                normalize_embeddings,
                show_progress
            )
            
            encode_time = time.time() - start_time
            logger.debug(f"Encoded {len(texts)} texts in {encode_time:.2f}s")
            
            if is_single:
                return embeddings[0]
            return embeddings
            
        except Exception as e:
            logger.error(f"Error encoding texts: {e}")
            raise
    
    def _encode_sync(
        self, 
        texts: List[str], 
        batch_size: int, 
        normalize_embeddings: bool,
        show_progress: bool
    ) -> np.ndarray:
        """Synchronous encoding"""
        return self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=normalize_embeddings,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )
    
    async def encode_documents(
        self, 
        documents: List[Dict[str, Any]], 
        content_field: str = 'content',
        title_field: Optional[str] = 'title',
        batch_size: int = 16
    ) -> List[Dict[str, Any]]:
        """
        Encode a list of documents with embeddings
        
        Args:
            documents: List of document dictionaries
            content_field: Field name containing the text content
            title_field: Optional field name for title (will be prepended)
            batch_size: Batch size for processing
            
        Returns:
            Documents with added 'embedding' field
        """
        if not documents:
            return []
        
        # Prepare texts for encoding
        texts = []
        for doc in documents:
            content = doc.get(content_field, '')
            title = doc.get(title_field, '') if title_field else ''
            
            # Combine title and content
            if title and content:
                text = f"{title}\n\n{content}"
            else:
                text = title or content
            
            texts.append(text)
        
        # Encode all texts
        embeddings = await self.encode_text(texts, batch_size=batch_size)
        
        # Add embeddings to documents
        result = []
        for i, doc in enumerate(documents):
            doc_with_embedding = doc.copy()
            doc_with_embedding['embedding'] = embeddings[i].tolist()
            result.append(doc_with_embedding)
        
        return result
    
    async def compute_similarity(
        self, 
        embedding1: Union[np.ndarray, List[float]], 
        embedding2: Union[np.ndarray, List[float]]
    ) -> float:
        """Compute cosine similarity between two embeddings"""
        try:
            # Convert to numpy arrays if needed
            if isinstance(embedding1, list):
                embedding1 = np.array(embedding1)
            if isinstance(embedding2, list):
                embedding2 = np.array(embedding2)
            
            # Compute cosine similarity
            dot_product = np.dot(embedding1, embedding2)
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error computing similarity: {e}")
            return 0.0
    
    async def find_similar_embeddings(
        self, 
        query_embedding: Union[np.ndarray, List[float]], 
        candidate_embeddings: List[Union[np.ndarray, List[float]]],
        top_k: int = 10,
        threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Find most similar embeddings to a query embedding
        
        Args:
            query_embedding: Query embedding
            candidate_embeddings: List of candidate embeddings
            top_k: Number of top results to return
            threshold: Minimum similarity threshold
            
        Returns:
            List of dictionaries with 'index' and 'similarity' keys
        """
        if not candidate_embeddings:
            return []
        
        try:
            # Compute similarities
            similarities = []
            for i, candidate in enumerate(candidate_embeddings):
                similarity = await self.compute_similarity(query_embedding, candidate)
                if similarity >= threshold:
                    similarities.append({
                        'index': i,
                        'similarity': similarity
                    })
            
            # Sort by similarity and return top_k
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            return similarities[:top_k]
            
        except Exception as e:
            logger.error(f"Error finding similar embeddings: {e}")
            return []
    
    async def switch_model(self, model_name: str):
        """Switch to a different embedding model"""
        if model_name == self.model_name:
            return
        
        logger.info(f"Switching embedding model from {self.model_name} to {model_name}")
        self.model_name = model_name
        await self._load_model(model_name)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model"""
        return {
            'model_name': self.model_name,
            'device': self.device,
            'is_loaded': self.model is not None,
            'available_models': self.DEFAULT_MODELS,
            'embedding_dimension': self.get_embedding_dimension()
        }
    
    def get_embedding_dimension(self) -> int:
        """Get the embedding dimension of the current model"""
        if self.model:
            return self.model.get_sentence_embedding_dimension()
        
        # Default dimensions for known models
        dimension_map = {
            'all-MiniLM-L6-v2': 384,
            'all-mpnet-base-v2': 768,
            'paraphrase-multilingual-MiniLM-L12-v2': 384,
            'microsoft/codebert-base': 768,
        }
        
        return dimension_map.get(self.model_name, 384)  # Default to 384
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the embedding service"""
        try:
            if not self.model:
                await self.initialize()
            
            # Test encoding
            test_text = "This is a test sentence for health check."
            start_time = time.time()
            embedding = await self.encode_text(test_text)
            encode_time = time.time() - start_time
            
            return {
                'status': 'healthy',
                'model_name': self.model_name,
                'device': self.device,
                'embedding_dimension': len(embedding),
                'test_encode_time': encode_time,
                'gpu_available': torch.cuda.is_available(),
                'gpu_memory': self._get_gpu_memory() if torch.cuda.is_available() else None
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'model_name': self.model_name,
                'device': self.device
            }
    
    def _get_gpu_memory(self) -> Optional[Dict[str, float]]:
        """Get GPU memory information"""
        try:
            if torch.cuda.is_available():
                return {
                    'allocated_gb': torch.cuda.memory_allocated() / 1024**3,
                    'reserved_gb': torch.cuda.memory_reserved() / 1024**3,
                    'total_gb': torch.cuda.get_device_properties(0).total_memory / 1024**3
                }
        except Exception:
            pass
        return None
    
    async def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up embedding service")
        
        # Clear model cache
        self._model_cache.clear()
        self.model = None
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        # Clear GPU cache if using CUDA
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

# Global embedding service instance
embedding_service = EmbeddingService()

# Convenience functions
async def encode_text(texts: Union[str, List[str]], **kwargs) -> Union[np.ndarray, List[np.ndarray]]:
    """Convenience function for encoding text"""
    return await embedding_service.encode_text(texts, **kwargs)

async def encode_documents(documents: List[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
    """Convenience function for encoding documents"""
    return await embedding_service.encode_documents(documents, **kwargs)

async def compute_similarity(embedding1: Union[np.ndarray, List[float]], embedding2: Union[np.ndarray, List[float]]) -> float:
    """Convenience function for computing similarity"""
    return await embedding_service.compute_similarity(embedding1, embedding2)