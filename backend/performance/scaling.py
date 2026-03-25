"""
Auto-Scaling System

This module provides automatic scaling capabilities based on:
- Resource utilization monitoring
- Performance metrics analysis
- Load prediction
- Scaling policies and rules
- Container and service scaling
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import redis
import docker
from kubernetes import client, config

logger = logging.getLogger(__name__)


class ScalingType(Enum):
    """Scaling types"""
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class ScalingAction(Enum):
    """Scaling actions"""
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    NO_ACTION = "no_action"


@dataclass
class ScalingPolicy:
    """Scaling policy configuration"""
    name: str
    service_name: str
    scaling_type: ScalingType
    min_instances: int
    max_instances: int
    target_cpu_percent: float
    target_memory_percent: float
    scale_up_threshold: float
    scale_down_threshold: float
    cooldown_period: int  # seconds
    enabled: bool = True


@dataclass
class ScalingDecision:
    """Scaling decision"""
    timestamp: datetime
    service_name: str
    action: ScalingAction
    current_instances: int
    target_instances: int
    reason: str
    metrics: Dict[str, float]


class AutoScaler:
    """Automatic scaling system"""
    
    def __init__(self, redis_url: str = "redis://localhost:6391"):
        self.redis_url = redis_url
        self.redis_client = redis.from_url(redis_url)
        
        # Scaling policies
        self.policies: Dict[str, ScalingPolicy] = {}
        
        # Scaling history
        self.scaling_history: List[ScalingDecision] = []
        
        # Docker client for container scaling
        self.docker_client = None
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.warning(f"Failed to initialize Docker client: {e}")
        
        # Kubernetes client for K8s scaling
        self.k8s_client = None
        try:
            config.load_incluster_config()
            self.k8s_client = client.AppsV1Api()
        except Exception as e:
            logger.warning(f"Failed to initialize Kubernetes client: {e}")
        
        # Scaling state
        self.is_scaling = False
        self.scaling_task = None
        
        # Cooldown tracking
        self.last_scaling_actions: Dict[str, datetime] = {}
        
        # Load prediction
        self.load_predictor = LoadPredictor()
        
        # Initialize default policies
        self._initialize_default_policies()
    
    def _initialize_default_policies(self):
        """Initialize default scaling policies"""
        default_policies = [
            ScalingPolicy(
                name="web_server",
                service_name="suna-frontend",
                scaling_type=ScalingType.HORIZONTAL,
                min_instances=2,
                max_instances=10,
                target_cpu_percent=70.0,
                target_memory_percent=80.0,
                scale_up_threshold=80.0,
                scale_down_threshold=30.0,
                cooldown_period=300
            ),
            ScalingPolicy(
                name="api_server",
                service_name="suna-backend",
                scaling_type=ScalingType.HORIZONTAL,
                min_instances=2,
                max_instances=15,
                target_cpu_percent=75.0,
                target_memory_percent=85.0,
                scale_up_threshold=85.0,
                scale_down_threshold=25.0,
                cooldown_period=300
            ),
            ScalingPolicy(
                name="database",
                service_name="suna-database",
                scaling_type=ScalingType.VERTICAL,
                min_instances=1,
                max_instances=1,
                target_cpu_percent=80.0,
                target_memory_percent=90.0,
                scale_up_threshold=90.0,
                scale_down_threshold=40.0,
                cooldown_period=600
            )
        ]
        
        for policy in default_policies:
            self.policies[policy.name] = policy
    
    async def start_scaling(self, interval: int = 60):
        """Start automatic scaling"""
        if self.is_scaling:
            logger.warning("Auto-scaling is already running")
            return
        
        self.is_scaling = True
        self.scaling_task = asyncio.create_task(
            self._scaling_loop(interval)
        )
        logger.info(f"Auto-scaling started with {interval}s interval")
    
    async def stop_scaling(self):
        """Stop automatic scaling"""
        if not self.is_scaling:
            return
        
        self.is_scaling = False
        if self.scaling_task:
            self.scaling_task.cancel()
            try:
                await self.scaling_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Auto-scaling stopped")
    
    async def _scaling_loop(self, interval: int):
        """Main scaling loop"""
        while self.is_scaling:
            try:
                # Evaluate scaling for each policy
                for policy_name, policy in self.policies.items():
                    if not policy.enabled:
                        continue
                    
                    # Check cooldown period
                    if not self._can_scale(policy):
                        continue
                    
                    # Get current metrics
                    metrics = await self._get_service_metrics(policy.service_name)
                    if not metrics:
                        continue
                    
                    # Make scaling decision
                    decision = await self._evaluate_scaling(policy, metrics)
                    
                    if decision.action != ScalingAction.NO_ACTION:
                        # Execute scaling
                        success = await self._execute_scaling(decision)
                        if success:
                            self.scaling_history.append(decision)
                            self.last_scaling_actions[policy.service_name] = datetime.now()
                            logger.info(f"Scaling executed: {decision}")
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in scaling loop: {e}")
                await asyncio.sleep(interval)
    
    def _can_scale(self, policy: ScalingPolicy) -> bool:
        """Check if scaling is allowed based on cooldown period"""
        last_action = self.last_scaling_actions.get(policy.service_name)
        if not last_action:
            return True
        
        time_since_last_action = (datetime.now() - last_action).total_seconds()
        return time_since_last_action >= policy.cooldown_period
    
    async def _get_service_metrics(self, service_name: str) -> Optional[Dict[str, float]]:
        """Get current metrics for a service"""
        try:
            # Get metrics from Redis
            metrics = {}
            
            # CPU usage
            cpu_key = f"service:{service_name}:cpu_percent"
            cpu_value = await self.redis_client.get(cpu_key)
            if cpu_value:
                metrics['cpu_percent'] = float(cpu_value)
            
            # Memory usage
            memory_key = f"service:{service_name}:memory_percent"
            memory_value = await self.redis_client.get(memory_key)
            if memory_value:
                metrics['memory_percent'] = float(memory_value)
            
            # Request rate
            request_key = f"service:{service_name}:request_rate"
            request_value = await self.redis_client.get(request_key)
            if request_value:
                metrics['request_rate'] = float(request_value)
            
            # Response time
            response_key = f"service:{service_name}:response_time"
            response_value = await self.redis_client.get(response_key)
            if response_value:
                metrics['response_time'] = float(response_value)
            
            return metrics if metrics else None
            
        except Exception as e:
            logger.error(f"Failed to get metrics for {service_name}: {e}")
            return None
    
    async def _evaluate_scaling(self, policy: ScalingPolicy, metrics: Dict[str, float]) -> ScalingDecision:
        """Evaluate scaling decision based on policy and metrics"""
        try:
            current_instances = await self._get_current_instances(policy.service_name)
            
            # Get predicted load
            predicted_load = await self.load_predictor.predict_load(policy.service_name)
            
            # Calculate scaling factors
            cpu_factor = metrics.get('cpu_percent', 0) / policy.target_cpu_percent
            memory_factor = metrics.get('memory_percent', 0) / policy.target_memory_percent
            load_factor = predicted_load / policy.target_cpu_percent if predicted_load > 0 else 1.0
            
            # Determine scaling action
            max_factor = max(cpu_factor, memory_factor, load_factor)
            
            if max_factor > policy.scale_up_threshold / 100:
                # Scale up
                target_instances = min(
                    policy.max_instances,
                    int(current_instances * max_factor)
                )
                
                if target_instances > current_instances:
                    return ScalingDecision(
                        timestamp=datetime.now(),
                        service_name=policy.service_name,
                        action=ScalingAction.SCALE_UP,
                        current_instances=current_instances,
                        target_instances=target_instances,
                        reason=f"High resource usage: CPU={metrics.get('cpu_percent', 0):.1f}%, Memory={metrics.get('memory_percent', 0):.1f}%",
                        metrics=metrics
                    )
            
            elif max_factor < policy.scale_down_threshold / 100:
                # Scale down
                target_instances = max(
                    policy.min_instances,
                    int(current_instances * max_factor)
                )
                
                if target_instances < current_instances:
                    return ScalingDecision(
                        timestamp=datetime.now(),
                        service_name=policy.service_name,
                        action=ScalingAction.SCALE_DOWN,
                        current_instances=current_instances,
                        target_instances=target_instances,
                        reason=f"Low resource usage: CPU={metrics.get('cpu_percent', 0):.1f}%, Memory={metrics.get('memory_percent', 0):.1f}%",
                        metrics=metrics
                    )
            
            return ScalingDecision(
                timestamp=datetime.now(),
                service_name=policy.service_name,
                action=ScalingAction.NO_ACTION,
                current_instances=current_instances,
                target_instances=current_instances,
                reason="No scaling needed",
                metrics=metrics
            )
            
        except Exception as e:
            logger.error(f"Failed to evaluate scaling: {e}")
            return ScalingDecision(
                timestamp=datetime.now(),
                service_name=policy.service_name,
                action=ScalingAction.NO_ACTION,
                current_instances=0,
                target_instances=0,
                reason=f"Error: {str(e)}",
                metrics={}
            )
    
    async def _get_current_instances(self, service_name: str) -> int:
        """Get current number of instances for a service"""
        try:
            # Try Docker first
            if self.docker_client:
                containers = self.docker_client.containers.list(
                    filters={"label": f"com.docker.compose.service={service_name}"}
                )
                if containers:
                    return len(containers)
            
            # Try Kubernetes
            if self.k8s_client:
                try:
                    deployment = self.k8s_client.read_namespaced_deployment(
                        name=service_name,
                        namespace="default"
                    )
                    return deployment.spec.replicas
                except Exception:
                    pass
            
            # Fallback to Redis
            instances_key = f"service:{service_name}:instances"
            instances_value = await self.redis_client.get(instances_key)
            return int(instances_value) if instances_value else 1
            
        except Exception as e:
            logger.error(f"Failed to get current instances for {service_name}: {e}")
            return 1
    
    async def _execute_scaling(self, decision: ScalingDecision) -> bool:
        """Execute scaling decision"""
        try:
            if decision.action == ScalingAction.SCALE_UP:
                return await self._scale_up(decision)
            elif decision.action == ScalingAction.SCALE_DOWN:
                return await self._scale_down(decision)
            else:
                return True
                
        except Exception as e:
            logger.error(f"Failed to execute scaling: {e}")
            return False
    
    async def _scale_up(self, decision: ScalingDecision) -> bool:
        """Scale up service"""
        try:
            logger.info(f"Scaling up {decision.service_name} from {decision.current_instances} to {decision.target_instances}")
            
            # Try Docker Compose scaling
            if self.docker_client:
                try:
                    # Scale using docker-compose
                    import subprocess
                    result = subprocess.run([
                        'docker-compose', 'up', '-d', 
                        f'{decision.service_name}={decision.target_instances}'
                    ], capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        await self._update_instance_count(decision.service_name, decision.target_instances)
                        return True
                except Exception as e:
                    logger.warning(f"Docker Compose scaling failed: {e}")
            
            # Try Kubernetes scaling
            if self.k8s_client:
                try:
                    patch = {
                        "spec": {
                            "replicas": decision.target_instances
                        }
                    }
                    
                    self.k8s_client.patch_namespaced_deployment(
                        name=decision.service_name,
                        namespace="default",
                        body=patch
                    )
                    
                    await self._update_instance_count(decision.service_name, decision.target_instances)
                    return True
                    
                except Exception as e:
                    logger.warning(f"Kubernetes scaling failed: {e}")
            
            # Fallback: update instance count in Redis
            await self._update_instance_count(decision.service_name, decision.target_instances)
            return True
            
        except Exception as e:
            logger.error(f"Failed to scale up {decision.service_name}: {e}")
            return False
    
    async def _scale_down(self, decision: ScalingDecision) -> bool:
        """Scale down service"""
        try:
            logger.info(f"Scaling down {decision.service_name} from {decision.current_instances} to {decision.target_instances}")
            
            # Try Docker Compose scaling
            if self.docker_client:
                try:
                    import subprocess
                    result = subprocess.run([
                        'docker-compose', 'up', '-d', 
                        f'{decision.service_name}={decision.target_instances}'
                    ], capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        await self._update_instance_count(decision.service_name, decision.target_instances)
                        return True
                except Exception as e:
                    logger.warning(f"Docker Compose scaling failed: {e}")
            
            # Try Kubernetes scaling
            if self.k8s_client:
                try:
                    patch = {
                        "spec": {
                            "replicas": decision.target_instances
                        }
                    }
                    
                    self.k8s_client.patch_namespaced_deployment(
                        name=decision.service_name,
                        namespace="default",
                        body=patch
                    )
                    
                    await self._update_instance_count(decision.service_name, decision.target_instances)
                    return True
                    
                except Exception as e:
                    logger.warning(f"Kubernetes scaling failed: {e}")
            
            # Fallback: update instance count in Redis
            await self._update_instance_count(decision.service_name, decision.target_instances)
            return True
            
        except Exception as e:
            logger.error(f"Failed to scale down {decision.service_name}: {e}")
            return False
    
    async def _update_instance_count(self, service_name: str, count: int):
        """Update instance count in Redis"""
        try:
            instances_key = f"service:{service_name}:instances"
            await self.redis_client.set(instances_key, count)
        except Exception as e:
            logger.error(f"Failed to update instance count: {e}")
    
    def add_policy(self, policy: ScalingPolicy):
        """Add a scaling policy"""
        self.policies[policy.name] = policy
        logger.info(f"Added scaling policy: {policy.name}")
    
    def remove_policy(self, policy_name: str):
        """Remove a scaling policy"""
        if policy_name in self.policies:
            del self.policies[policy_name]
            logger.info(f"Removed scaling policy: {policy_name}")
    
    def update_policy(self, policy_name: str, **kwargs):
        """Update a scaling policy"""
        if policy_name in self.policies:
            policy = self.policies[policy_name]
            for key, value in kwargs.items():
                if hasattr(policy, key):
                    setattr(policy, key, value)
            logger.info(f"Updated scaling policy: {policy_name}")
    
    async def get_scaling_summary(self) -> Dict[str, Any]:
        """Get scaling summary"""
        try:
            recent_decisions = [
                d for d in self.scaling_history 
                if d.timestamp > datetime.now() - timedelta(hours=24)
            ]
            
            scale_ups = len([d for d in recent_decisions if d.action == ScalingAction.SCALE_UP])
            scale_downs = len([d for d in recent_decisions if d.action == ScalingAction.SCALE_DOWN])
            
            return {
                'is_scaling': self.is_scaling,
                'policies_count': len(self.policies),
                'enabled_policies': len([p for p in self.policies.values() if p.enabled]),
                'recent_decisions': len(recent_decisions),
                'scale_ups_24h': scale_ups,
                'scale_downs_24h': scale_downs,
                'last_scaling_actions': {
                    service: action.isoformat() 
                    for service, action in self.last_scaling_actions.items()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get scaling summary: {e}")
            return {}
    
    async def manual_scale(self, service_name: str, target_instances: int) -> bool:
        """Manually scale a service"""
        try:
            current_instances = await self._get_current_instances(service_name)
            
            decision = ScalingDecision(
                timestamp=datetime.now(),
                service_name=service_name,
                action=ScalingAction.SCALE_UP if target_instances > current_instances else ScalingAction.SCALE_DOWN,
                current_instances=current_instances,
                target_instances=target_instances,
                reason="Manual scaling",
                metrics={}
            )
            
            success = await self._execute_scaling(decision)
            if success:
                self.scaling_history.append(decision)
                self.last_scaling_actions[service_name] = datetime.now()
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to manually scale {service_name}: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup scaling resources"""
        try:
            await self.stop_scaling()
            logger.info("Auto-scaler cleanup completed")
        except Exception as e:
            logger.error(f"Failed to cleanup auto-scaler: {e}")


class LoadPredictor:
    """Load prediction for proactive scaling"""
    
    def __init__(self):
        self.historical_data = {}
        self.prediction_window = 300  # 5 minutes
    
    async def predict_load(self, service_name: str) -> float:
        """Predict load for a service"""
        try:
            # Simple moving average prediction
            # In production, use more sophisticated ML models
            
            if service_name not in self.historical_data:
                return 0.0
            
            recent_data = self.historical_data[service_name][-10:]  # Last 10 data points
            if not recent_data:
                return 0.0
            
            # Calculate trend
            if len(recent_data) >= 2:
                trend = (recent_data[-1] - recent_data[0]) / len(recent_data)
                prediction = recent_data[-1] + trend
            else:
                prediction = recent_data[-1]
            
            return max(0.0, prediction)
            
        except Exception as e:
            logger.error(f"Failed to predict load for {service_name}: {e}")
            return 0.0
    
    def add_data_point(self, service_name: str, load_value: float):
        """Add a data point for load prediction"""
        if service_name not in self.historical_data:
            self.historical_data[service_name] = []
        
        self.historical_data[service_name].append(load_value)
        
        # Keep only recent data
        if len(self.historical_data[service_name]) > 100:
            self.historical_data[service_name] = self.historical_data[service_name][-50:]







