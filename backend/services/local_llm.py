"""
Local LLM service using Ollama for model inference.

This module provides a unified interface for local LLM inference using Ollama,
with support for model management, performance monitoring, and fallback to
external APIs when local models are not available.
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, Optional, List, Union, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
import logging

from utils.logger import logger
from utils.config import config
from services.llm import make_llm_api_call, LLMError

class ModelStatus(Enum):
    """Model status enumeration."""
    AVAILABLE = "available"
    LOADING = "loading"
    UNAVAILABLE = "unavailable"
    ERROR = "error"

@dataclass
class ModelInfo:
    """Model information."""
    name: str
    size: int
    modified_at: str
    digest: str
    status: ModelStatus = ModelStatus.UNAVAILABLE

@dataclass
class ModelPerformance:
    """Model performance metrics."""
    model_name: str
    response_time_ms: float
    tokens_per_second: float
    memory_usage_mb: float
    timestamp: float

class LocalLLMService:
    """Local LLM service using Ollama."""
    
    def __init__(self):
        self.base_url = config.OLLAMA_BASE_URL or "http://localhost:11434"
        self.session: Optional[aiohttp.ClientSession] = None
        self.available_models: Dict[str, ModelInfo] = {}
        self.model_performance: List[ModelPerformance] = []
        self._initialized = False
        
    async def initialize(self):
        """Initialize the service and check available models."""
        if self._initialized:
            return
            
        self.session = aiohttp.ClientSession()
        await self._refresh_models()
        self._initialized = True
        logger.info(f"Local LLM service initialized with {len(self.available_models)} models")
    
    async def _refresh_models(self):
        """Refresh the list of available models."""
        try:
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    self.available_models.clear()
                    
                    for model in data.get("models", []):
                        model_info = ModelInfo(
                            name=model["name"],
                            size=model.get("size", 0),
                            modified_at=model.get("modified_at", ""),
                            digest=model.get("digest", ""),
                            status=ModelStatus.AVAILABLE
                        )
                        self.available_models[model["name"]] = model_info
                        
                    logger.debug(f"Found {len(self.available_models)} available models")
                else:
                    logger.warning(f"Failed to get models from Ollama: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error refreshing models: {e}")
            # Mark all configured models as unavailable
            for model_name in config.LOCAL_MODELS.keys():
                self.available_models[model_name] = ModelInfo(
                    name=model_name,
                    size=0,
                    modified_at="",
                    digest="",
                    status=ModelStatus.UNAVAILABLE
                )
    
    async def is_model_available(self, model_name: str) -> bool:
        """Check if a model is available locally."""
        if not self._initialized:
            await self.initialize()
        
        return model_name in self.available_models and \
               self.available_models[model_name].status == ModelStatus.AVAILABLE
    
    async def get_available_models(self) -> List[str]:
        """Get list of available model names."""
        if not self._initialized:
            await self.initialize()
        
        return [name for name, info in self.available_models.items() 
                if info.status == ModelStatus.AVAILABLE]
    
    async def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama library."""
        if not self._initialized:
            await self.initialize()
        
        try:
            logger.info(f"Pulling model: {model_name}")
            
            # Start the pull request
            async with self.session.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name}
            ) as response:
                if response.status == 200:
                    # Monitor the pull progress
                    async for line in response.content:
                        if line:
                            try:
                                data = json.loads(line.decode())
                                if data.get("status") == "success":
                                    logger.info(f"Successfully pulled model: {model_name}")
                                    await self._refresh_models()
                                    return True
                                elif data.get("status") == "error":
                                    logger.error(f"Failed to pull model {model_name}: {data.get('error')}")
                                    return False
                            except json.JSONDecodeError:
                                continue
                else:
                    logger.error(f"Failed to start pull for model {model_name}: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error pulling model {model_name}: {e}")
            return False
        
        return False
    
    async def generate(
        self,
        model_name: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[Dict[str, Any], AsyncGenerator]:
        """Generate text using a local model."""
        if not self._initialized:
            await self.initialize()
        
        # Check if model is available
        if not await self.is_model_available(model_name):
            logger.warning(f"Model {model_name} not available locally, attempting to pull")
            if not await self.pull_model(model_name):
                raise LLMError(f"Model {model_name} not available and could not be pulled")
        
        # Prepare the request
        request_data = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "stream": stream
        }
        
        if max_tokens:
            request_data["num_predict"] = max_tokens
        
        # Add any additional parameters
        request_data.update(kwargs)
        
        start_time = time.time()
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/generate",
                json=request_data
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise LLMError(f"Ollama API error: {response.status} - {error_text}")
                
                if stream:
                    return self._handle_stream_response(response, model_name, start_time)
                else:
                    return await self._handle_complete_response(response, model_name, start_time)
                    
        except Exception as e:
            logger.error(f"Error generating with model {model_name}: {e}")
            raise LLMError(f"Generation failed: {str(e)}")
    
    async def _handle_complete_response(
        self, 
        response: aiohttp.ClientResponse, 
        model_name: str, 
        start_time: float
    ) -> Dict[str, Any]:
        """Handle complete (non-streaming) response."""
        response_text = ""
        
        async for line in response.content:
            if line:
                try:
                    data = json.loads(line.decode())
                    if "response" in data:
                        response_text += data["response"]
                    if data.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue
        
        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        # Record performance metrics
        await self._record_performance(model_name, response_time, len(response_text.split()))
        
        return {
            "choices": [{
                "message": {
                    "content": response_text,
                    "role": "assistant"
                },
                "finish_reason": "stop"
            }],
            "model": model_name,
            "usage": {
                "prompt_tokens": 0,  # Ollama doesn't provide token counts
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }
    
    async def _handle_stream_response(
        self, 
        response: aiohttp.ClientResponse, 
        model_name: str, 
        start_time: float
    ) -> AsyncGenerator:
        """Handle streaming response."""
        async for line in response.content:
            if line:
                try:
                    data = json.loads(line.decode())
                    
                    if "response" in data:
                        yield {
                            "choices": [{
                                "delta": {
                                    "content": data["response"]
                                },
                                "finish_reason": None
                            }],
                            "model": model_name
                        }
                    
                    if data.get("done", False):
                        end_time = time.time()
                        response_time = (end_time - start_time) * 1000
                        
                        # Record performance metrics
                        await self._record_performance(model_name, response_time, 0)
                        
                        yield {
                            "choices": [{
                                "delta": {},
                                "finish_reason": "stop"
                            }],
                            "model": model_name
                        }
                        break
                        
                except json.JSONDecodeError:
                    continue
    
    async def _record_performance(self, model_name: str, response_time_ms: float, token_count: int):
        """Record performance metrics for a model."""
        tokens_per_second = (token_count / (response_time_ms / 1000)) if response_time_ms > 0 else 0
        
        performance = ModelPerformance(
            model_name=model_name,
            response_time_ms=response_time_ms,
            tokens_per_second=tokens_per_second,
            memory_usage_mb=0,  # Ollama doesn't provide memory usage
            timestamp=time.time()
        )
        
        self.model_performance.append(performance)
        
        # Keep only last 1000 performance records
        if len(self.model_performance) > 1000:
            self.model_performance = self.model_performance[-1000:]
    
    async def get_model_performance(self, model_name: Optional[str] = None) -> List[ModelPerformance]:
        """Get performance metrics for models."""
        if model_name:
            return [p for p in self.model_performance if p.model_name == model_name]
        return self.model_performance.copy()
    
    async def get_recommended_model(self, use_case: str) -> Optional[str]:
        """Get recommended model for a specific use case."""
        if not self._initialized:
            await self.initialize()
        
        # Check if we have a default model for this use case
        default_model = config.DEFAULT_LOCAL_MODELS.get(use_case)
        if default_model and await self.is_model_available(default_model):
            return default_model
        
        # Find any available model that's recommended for this use case
        for model_name, model_config in config.LOCAL_MODELS.items():
            if (use_case in model_config.get('recommended_for', []) and 
                await self.is_model_available(model_name)):
                return model_name
        
        # Fall back to any available model
        available_models = await self.get_available_models()
        if available_models:
            return available_models[0]
        
        return None
    
    async def close(self):
        """Close the service and cleanup resources."""
        if self.session:
            await self.session.close()
        self._initialized = False

# Global instance
local_llm_service = LocalLLMService()

async def make_local_llm_call(
    messages: List[Dict[str, Any]],
    model_name: str,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    stream: bool = False,
    **kwargs
) -> Union[Dict[str, Any], AsyncGenerator]:
    """
    Make a call to a local LLM model with fallback to external APIs.
    
    Args:
        messages: List of message dictionaries
        model_name: Name of the model to use
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        stream: Whether to stream the response
        **kwargs: Additional parameters
    
    Returns:
        API response or stream
    
    Raises:
        LLMError: If both local and external calls fail
    """
    # Check if local LLM is enabled
    if not config.ENABLE_LOCAL_LLM:
        logger.debug("Local LLM disabled, using external API")
        return await make_llm_api_call(
            messages=messages,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            **kwargs
        )
    
    try:
        # Try local model first
        logger.debug(f"Attempting local LLM call with model: {model_name}")
        return await local_llm_service.generate(
            model_name=model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            **kwargs
        )
    except Exception as e:
        logger.warning(f"Local LLM call failed: {e}, falling back to external API")
        
        # Fall back to external API
        try:
            return await make_llm_api_call(
                messages=messages,
                model_name=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                **kwargs
            )
        except Exception as external_error:
            logger.error(f"Both local and external LLM calls failed: {external_error}")
            raise LLMError(f"All LLM providers failed: local={e}, external={external_error}")

async def initialize_local_llm():
    """Initialize the local LLM service."""
    await local_llm_service.initialize()



