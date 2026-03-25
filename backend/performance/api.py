"""
Performance Optimization API

This module provides FastAPI endpoints for:
- Performance monitoring and metrics
- Database optimization
- Caching management
- Auto-scaling control
- Container optimization
- Performance alerts and recommendations
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio
import logging

from .database import DatabaseOptimizer
from .caching import CacheManager
from .monitoring import PerformanceMonitor
from .scaling import AutoScaler
from .container import ContainerOptimizer

logger = logging.getLogger(__name__)

# Initialize performance optimization components
db_optimizer = DatabaseOptimizer()
cache_manager = CacheManager()
performance_monitor = PerformanceMonitor()
auto_scaler = AutoScaler()
container_optimizer = ContainerOptimizer()

# Create API router
router = APIRouter(prefix="/api/v1/performance", tags=["performance"])


@router.on_event("startup")
async def startup_event():
    """Initialize performance optimization components on startup"""
    try:
        # Start monitoring services
        await performance_monitor.start_monitoring()
        await auto_scaler.start_scaling()
        await container_optimizer.start_monitoring()
        
        logger.info("Performance optimization services started")
    except Exception as e:
        logger.error(f"Failed to start performance optimization services: {e}")


@router.on_event("shutdown")
async def shutdown_event():
    """Cleanup performance optimization components on shutdown"""
    try:
        await performance_monitor.cleanup()
        await auto_scaler.cleanup()
        await container_optimizer.cleanup()
        await db_optimizer.cleanup()
        await cache_manager.cleanup()
        
        logger.info("Performance optimization services stopped")
    except Exception as e:
        logger.error(f"Failed to stop performance optimization services: {e}")


# Database Optimization Endpoints

@router.get("/database/status")
async def get_database_status():
    """Get database optimization status and metrics"""
    try:
        summary = await db_optimizer.get_performance_summary()
        return JSONResponse(content=summary)
    except Exception as e:
        logger.error(f"Failed to get database status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/database/optimize")
async def optimize_database(table_name: Optional[str] = None):
    """Optimize database performance"""
    try:
        if table_name:
            # Optimize specific table
            success = await db_optimizer.optimize_table_indexes(table_name)
            if success:
                return {"message": f"Database table {table_name} optimized successfully"}
            else:
                raise HTTPException(status_code=500, detail=f"Failed to optimize table {table_name}")
        else:
            # Generate recommendations for all tables
            recommendations = await db_optimizer.generate_index_recommendations()
            return {"recommendations": [r.__dict__ for r in recommendations]}
    except Exception as e:
        logger.error(f"Failed to optimize database: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/database/tables/{table_name}/stats")
async def get_table_statistics(table_name: str):
    """Get detailed statistics for a specific table"""
    try:
        stats = await db_optimizer.get_table_statistics(table_name)
        return JSONResponse(content=stats)
    except Exception as e:
        logger.error(f"Failed to get table statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Caching Endpoints

@router.get("/cache/status")
async def get_cache_status():
    """Get cache performance status and statistics"""
    try:
        stats = await cache_manager.get_cache_stats()
        return JSONResponse(content=stats)
    except Exception as e:
        logger.error(f"Failed to get cache status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/optimize")
async def optimize_cache():
    """Optimize cache performance"""
    try:
        success = await cache_manager.optimize_cache()
        if success:
            return {"message": "Cache optimized successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to optimize cache")
    except Exception as e:
        logger.error(f"Failed to optimize cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/invalidate")
async def invalidate_cache(
    cache_type: str,
    target: Optional[str] = None
):
    """Invalidate cache entries"""
    try:
        if cache_type == "user" and target:
            await cache_manager.invalidate_user_cache(target)
        elif cache_type == "session" and target:
            await cache_manager.invalidate_session_cache(target)
        elif cache_type == "table" and target:
            await cache_manager.invalidate_table_cache(target)
        else:
            raise HTTPException(status_code=400, detail="Invalid cache type or missing target")
        
        return {"message": f"Cache invalidated for {cache_type}: {target}"}
    except Exception as e:
        logger.error(f"Failed to invalidate cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/warm")
async def warm_cache(warmup_data: Dict[str, Any]):
    """Warm up cache with frequently accessed data"""
    try:
        success = await cache_manager.warm_cache(warmup_data)
        if success:
            return {"message": f"Cache warmed up with {len(warmup_data)} items"}
        else:
            raise HTTPException(status_code=500, detail="Failed to warm cache")
    except Exception as e:
        logger.error(f"Failed to warm cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Performance Monitoring Endpoints

@router.get("/monitoring/status")
async def get_monitoring_status():
    """Get performance monitoring status"""
    try:
        summary = await performance_monitor.get_performance_summary()
        return JSONResponse(content=summary)
    except Exception as e:
        logger.error(f"Failed to get monitoring status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitoring/bottlenecks")
async def identify_bottlenecks():
    """Identify performance bottlenecks"""
    try:
        bottlenecks = await performance_monitor.identify_bottlenecks()
        return JSONResponse(content={"bottlenecks": bottlenecks})
    except Exception as e:
        logger.error(f"Failed to identify bottlenecks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitoring/metrics/{metric_type}")
async def get_historical_metrics(
    metric_type: str,
    hours: int = 24
):
    """Get historical performance metrics"""
    try:
        metrics = await performance_monitor.get_historical_metrics(metric_type, hours)
        return JSONResponse(content={"metrics": metrics})
    except Exception as e:
        logger.error(f"Failed to get historical metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitoring/alerts/callback")
async def add_alert_callback(callback_url: str):
    """Add performance alert callback"""
    try:
        # This would typically register a webhook URL
        # For now, we'll just log it
        logger.info(f"Alert callback registered: {callback_url}")
        return {"message": "Alert callback registered successfully"}
    except Exception as e:
        logger.error(f"Failed to add alert callback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Auto-Scaling Endpoints

@router.get("/scaling/status")
async def get_scaling_status():
    """Get auto-scaling status and configuration"""
    try:
        summary = await auto_scaler.get_scaling_summary()
        return JSONResponse(content=summary)
    except Exception as e:
        logger.error(f"Failed to get scaling status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scaling/manual")
async def manual_scale(
    service_name: str,
    target_instances: int
):
    """Manually scale a service"""
    try:
        success = await auto_scaler.manual_scale(service_name, target_instances)
        if success:
            return {"message": f"Service {service_name} scaled to {target_instances} instances"}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to scale service {service_name}")
    except Exception as e:
        logger.error(f"Failed to manually scale: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scaling/policies")
async def get_scaling_policies():
    """Get all scaling policies"""
    try:
        policies = []
        for name, policy in auto_scaler.policies.items():
            policies.append({
                "name": name,
                "service_name": policy.service_name,
                "scaling_type": policy.scaling_type.value,
                "min_instances": policy.min_instances,
                "max_instances": policy.max_instances,
                "target_cpu_percent": policy.target_cpu_percent,
                "target_memory_percent": policy.target_memory_percent,
                "enabled": policy.enabled
            })
        return JSONResponse(content={"policies": policies})
    except Exception as e:
        logger.error(f"Failed to get scaling policies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scaling/policies")
async def add_scaling_policy(policy_data: Dict[str, Any]):
    """Add a new scaling policy"""
    try:
        from .scaling import ScalingPolicy, ScalingType
        
        policy = ScalingPolicy(
            name=policy_data["name"],
            service_name=policy_data["service_name"],
            scaling_type=ScalingType(policy_data["scaling_type"]),
            min_instances=policy_data["min_instances"],
            max_instances=policy_data["max_instances"],
            target_cpu_percent=policy_data["target_cpu_percent"],
            target_memory_percent=policy_data["target_memory_percent"],
            scale_up_threshold=policy_data["scale_up_threshold"],
            scale_down_threshold=policy_data["scale_down_threshold"],
            cooldown_period=policy_data["cooldown_period"],
            enabled=policy_data.get("enabled", True)
        )
        
        auto_scaler.add_policy(policy)
        return {"message": f"Scaling policy {policy.name} added successfully"}
    except Exception as e:
        logger.error(f"Failed to add scaling policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Container Optimization Endpoints

@router.get("/containers/status")
async def get_container_status():
    """Get container optimization status"""
    try:
        summary = await container_optimizer.get_optimization_summary()
        return JSONResponse(content=summary)
    except Exception as e:
        logger.error(f"Failed to get container status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/containers/{container_name}/performance")
async def get_container_performance(container_name: str):
    """Get performance analysis for a specific container"""
    try:
        analysis = await container_optimizer.analyze_container_performance(container_name)
        return JSONResponse(content=analysis)
    except Exception as e:
        logger.error(f"Failed to get container performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/containers/{container_name}/recommendations")
async def get_container_recommendations(container_name: str):
    """Get optimization recommendations for a container"""
    try:
        recommendations = await container_optimizer.generate_optimization_recommendations(container_name)
        return JSONResponse(content={"recommendations": [r.__dict__ for r in recommendations]})
    except Exception as e:
        logger.error(f"Failed to get container recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/containers/{container_name}/optimize")
async def apply_container_optimization(
    container_name: str,
    optimization_type: str,
    new_value: Any
):
    """Apply optimization to a container"""
    try:
        success = await container_optimizer.apply_optimization(container_name, optimization_type, new_value)
        if success:
            return {"message": f"Optimization {optimization_type}={new_value} applied to {container_name}"}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to apply optimization to {container_name}")
    except Exception as e:
        logger.error(f"Failed to apply container optimization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/containers/{container_name}/startup")
async def optimize_container_startup(container_name: str):
    """Get container startup optimization recommendations"""
    try:
        optimization = await container_optimizer.optimize_startup_time(container_name)
        return JSONResponse(content=optimization)
    except Exception as e:
        logger.error(f"Failed to optimize container startup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Overall Performance Endpoints

@router.get("/overview")
async def get_performance_overview():
    """Get comprehensive performance overview"""
    try:
        # Gather data from all components
        db_summary = await db_optimizer.get_performance_summary()
        cache_stats = await cache_manager.get_cache_stats()
        monitoring_summary = await performance_monitor.get_performance_summary()
        scaling_summary = await auto_scaler.get_scaling_summary()
        container_summary = await container_optimizer.get_optimization_summary()
        
        # Identify bottlenecks
        bottlenecks = await performance_monitor.identify_bottlenecks()
        
        overview = {
            "timestamp": datetime.now().isoformat(),
            "database": db_summary,
            "cache": cache_stats,
            "monitoring": monitoring_summary,
            "scaling": scaling_summary,
            "containers": container_summary,
            "bottlenecks": bottlenecks,
            "system_health": _calculate_system_health(
                db_summary, cache_stats, monitoring_summary, bottlenecks
            )
        }
        
        return JSONResponse(content=overview)
    except Exception as e:
        logger.error(f"Failed to get performance overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimize/all")
async def optimize_all(background_tasks: BackgroundTasks):
    """Run comprehensive performance optimization"""
    try:
        # Add optimization tasks to background
        background_tasks.add_task(_run_database_optimization)
        background_tasks.add_task(_run_cache_optimization)
        background_tasks.add_task(_run_container_optimization)
        
        return {"message": "Performance optimization started in background"}
    except Exception as e:
        logger.error(f"Failed to start optimization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _calculate_system_health(
    db_summary: Dict,
    cache_stats: Dict,
    monitoring_summary: Dict,
    bottlenecks: List
) -> str:
    """Calculate overall system health"""
    try:
        # Check database health
        db_healthy = db_summary.get('slow_query_count', 0) < 10
        
        # Check cache health
        cache_hit_rate = cache_stats.get('hit_rate', 0)
        cache_healthy = cache_hit_rate > 70
        
        # Check monitoring health
        monitoring_healthy = not monitoring_summary.get('error')
        
        # Check for critical bottlenecks
        critical_bottlenecks = [b for b in bottlenecks if b.get('severity') == 'critical']
        
        if critical_bottlenecks:
            return "critical"
        elif not db_healthy or not cache_healthy:
            return "warning"
        elif monitoring_healthy:
            return "healthy"
        else:
            return "unknown"
    except Exception:
        return "unknown"


async def _run_database_optimization():
    """Background task for database optimization"""
    try:
        # Generate and apply index recommendations
        recommendations = await db_optimizer.generate_index_recommendations()
        for rec in recommendations:
            await db_optimizer.optimize_table_indexes(rec.table_name)
        
        logger.info("Database optimization completed")
    except Exception as e:
        logger.error(f"Database optimization failed: {e}")


async def _run_cache_optimization():
    """Background task for cache optimization"""
    try:
        await cache_manager.optimize_cache()
        logger.info("Cache optimization completed")
    except Exception as e:
        logger.error(f"Cache optimization failed: {e}")


async def _run_container_optimization():
    """Background task for container optimization"""
    try:
        # Get all containers and apply optimizations
        containers = await container_optimizer._get_all_containers()
        for container in containers:
            recommendations = await container_optimizer.generate_optimization_recommendations(container.name)
            for rec in recommendations:
                if rec.priority in ['critical', 'high']:
                    await container_optimizer.apply_optimization(
                        container.name, rec.recommendation_type, rec.recommended_value
                    )
        
        logger.info("Container optimization completed")
    except Exception as e:
        logger.error(f"Container optimization failed: {e}")


# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check for performance optimization services"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "database_optimizer": True,
                "cache_manager": True,
                "performance_monitor": performance_monitor.is_monitoring,
                "auto_scaler": auto_scaler.is_scaling,
                "container_optimizer": container_optimizer.is_monitoring
            }
        }
        return JSONResponse(content=health_status)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))







