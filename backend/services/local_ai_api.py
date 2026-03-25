"""
API endpoints for local AI/ML services management.

This module provides REST API endpoints for managing local LLM models,
monitoring performance, and configuring local AI services.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
import asyncio

from services.local_llm import local_llm_service, ModelInfo, ModelPerformance
from services.embedding_service import EmbeddingService
from utils.config import config
from utils.logger import logger

router = APIRouter(prefix="/api/local-ai", tags=["local-ai"])

# Pydantic models for API requests/responses
class ModelListResponse(BaseModel):
    """Response model for available models."""
    models: List[Dict[str, Any]]
    total_count: int
    local_enabled: bool

class ModelPullRequest(BaseModel):
    """Request model for pulling a model."""
    model_name: str

class ModelPullResponse(BaseModel):
    """Response model for model pull operation."""
    success: bool
    message: str
    model_name: str

class PerformanceMetricsResponse(BaseModel):
    """Response model for performance metrics."""
    model_name: str
    avg_response_time_ms: float
    avg_tokens_per_second: float
    total_requests: int
    recent_performance: List[Dict[str, Any]]

class LocalAIConfigResponse(BaseModel):
    """Response model for local AI configuration."""
    ollama_enabled: bool
    ollama_base_url: Optional[str]
    embedding_enabled: bool
    gpu_acceleration: bool
    model_monitoring: bool
    available_models: List[str]
    configured_models: Dict[str, Any]

@router.get("/models", response_model=ModelListResponse)
async def get_available_models():
    """Get list of available local models."""
    try:
        await local_llm_service.initialize()
        available_models = await local_llm_service.get_available_models()
        
        models_data = []
        for model_name in available_models:
            model_info = local_llm_service.available_models.get(model_name)
            model_config = config.LOCAL_MODELS.get(model_name, {})
            
            models_data.append({
                "name": model_name,
                "display_name": model_config.get("name", model_name),
                "description": model_config.get("description", ""),
                "size": model_info.size if model_info else 0,
                "context_length": model_config.get("context_length", 4096),
                "recommended_for": model_config.get("recommended_for", []),
                "gpu_memory_gb": model_config.get("gpu_memory_gb", 0),
                "cpu_memory_gb": model_config.get("cpu_memory_gb", 0),
                "status": "available"
            })
        
        return ModelListResponse(
            models=models_data,
            total_count=len(models_data),
            local_enabled=config.ENABLE_LOCAL_LLM
        )
        
    except Exception as e:
        logger.error(f"Error getting available models: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get models: {str(e)}")

@router.post("/models/pull", response_model=ModelPullResponse)
async def pull_model(request: ModelPullRequest, background_tasks: BackgroundTasks):
    """Pull a model from Ollama library."""
    try:
        # Validate model name
        if request.model_name not in config.LOCAL_MODELS:
            raise HTTPException(
                status_code=400, 
                detail=f"Model {request.model_name} not in configured models"
            )
        
        # Check if already available
        if await local_llm_service.is_model_available(request.model_name):
            return ModelPullResponse(
                success=True,
                message=f"Model {request.model_name} is already available",
                model_name=request.model_name
            )
        
        # Start pull in background
        background_tasks.add_task(local_llm_service.pull_model, request.model_name)
        
        return ModelPullResponse(
            success=True,
            message=f"Started pulling model {request.model_name}",
            model_name=request.model_name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pulling model {request.model_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to pull model: {str(e)}")

@router.get("/models/{model_name}/performance", response_model=PerformanceMetricsResponse)
async def get_model_performance(model_name: str):
    """Get performance metrics for a specific model."""
    try:
        performance_data = await local_llm_service.get_model_performance(model_name)
        
        if not performance_data:
            raise HTTPException(
                status_code=404,
                detail=f"No performance data available for model {model_name}"
            )
        
        # Calculate averages
        total_requests = len(performance_data)
        avg_response_time = sum(p.response_time_ms for p in performance_data) / total_requests
        avg_tokens_per_second = sum(p.tokens_per_second for p in performance_data) / total_requests
        
        # Get recent performance (last 10 entries)
        recent_performance = []
        for p in performance_data[-10:]:
            recent_performance.append({
                "response_time_ms": p.response_time_ms,
                "tokens_per_second": p.tokens_per_second,
                "memory_usage_mb": p.memory_usage_mb,
                "timestamp": p.timestamp
            })
        
        return PerformanceMetricsResponse(
            model_name=model_name,
            avg_response_time_ms=avg_response_time,
            avg_tokens_per_second=avg_tokens_per_second,
            total_requests=total_requests,
            recent_performance=recent_performance
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting performance for model {model_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get performance: {str(e)}")

@router.get("/models/recommended/{use_case}")
async def get_recommended_model(use_case: str):
    """Get recommended model for a specific use case."""
    try:
        recommended_model = await local_llm_service.get_recommended_model(use_case)
        
        if not recommended_model:
            raise HTTPException(
                status_code=404,
                detail=f"No recommended model found for use case: {use_case}"
            )
        
        model_config = config.LOCAL_MODELS.get(recommended_model, {})
        
        return {
            "model_name": recommended_model,
            "display_name": model_config.get("name", recommended_model),
            "description": model_config.get("description", ""),
            "use_case": use_case,
            "recommended_for": model_config.get("recommended_for", [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recommended model for {use_case}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get recommended model: {str(e)}")

@router.get("/config", response_model=LocalAIConfigResponse)
async def get_local_ai_config():
    """Get local AI configuration and status."""
    try:
        await local_llm_service.initialize()
        available_models = await local_llm_service.get_available_models()
        
        return LocalAIConfigResponse(
            ollama_enabled=config.ENABLE_LOCAL_LLM,
            ollama_base_url=config.OLLAMA_BASE_URL,
            embedding_enabled=config.ENABLE_LOCAL_EMBEDDINGS,
            gpu_acceleration=config.ENABLE_GPU_ACCELERATION,
            model_monitoring=config.ENABLE_MODEL_MONITORING,
            available_models=available_models,
            configured_models=config.LOCAL_MODELS
        )
        
    except Exception as e:
        logger.error(f"Error getting local AI config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get config: {str(e)}")

@router.post("/models/{model_name}/test")
async def test_model(model_name: str):
    """Test a local model with a simple prompt."""
    try:
        # Check if model is available
        if not await local_llm_service.is_model_available(model_name):
            raise HTTPException(
                status_code=404,
                detail=f"Model {model_name} is not available"
            )
        
        # Simple test prompt
        test_messages = [
            {"role": "user", "content": "Hello! Please respond with 'Local model test successful' if you can see this message."}
        ]
        
        response = await local_llm_service.generate(
            model_name=model_name,
            messages=test_messages,
            temperature=0.1,
            max_tokens=50
        )
        
        return {
            "success": True,
            "model_name": model_name,
            "response": response["choices"][0]["message"]["content"],
            "test_completed": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing model {model_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Model test failed: {str(e)}")

@router.get("/health")
async def get_local_ai_health():
    """Get health status of local AI services."""
    try:
        await local_llm_service.initialize()
        
        # Check Ollama connectivity
        ollama_healthy = len(await local_llm_service.get_available_models()) > 0
        
        # Check embedding service
        embedding_healthy = False
        try:
            embedding_service = EmbeddingService()
            await embedding_service.initialize()
            embedding_healthy = True
        except Exception as e:
            logger.warning(f"Embedding service not healthy: {e}")
        
        return {
            "status": "healthy" if (ollama_healthy or embedding_healthy) else "degraded",
            "services": {
                "ollama": {
                    "status": "healthy" if ollama_healthy else "unavailable",
                    "available_models": len(await local_llm_service.get_available_models())
                },
                "embeddings": {
                    "status": "healthy" if embedding_healthy else "unavailable"
                }
            },
            "config": {
                "local_llm_enabled": config.ENABLE_LOCAL_LLM,
                "local_embeddings_enabled": config.ENABLE_LOCAL_EMBEDDINGS,
                "gpu_acceleration": config.ENABLE_GPU_ACCELERATION
            }
        }
        
    except Exception as e:
        logger.error(f"Error checking local AI health: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")



