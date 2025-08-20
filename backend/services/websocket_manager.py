"""
WebSocket manager to replace Supabase real-time functionality.
Provides real-time communication for threads, messages, and agent status updates.
"""

import json
import asyncio
from typing import Dict, Set, Optional, Any, List
from fastapi import WebSocket, WebSocketDisconnect
from utils.logger import logger
from datetime import datetime, timezone
import uuid

class ConnectionManager:
    """Manages WebSocket connections and real-time messaging"""
    
    def __init__(self):
        # Active connections by connection ID
        self.active_connections: Dict[str, WebSocket] = {}
        
        # User connections mapping
        self.user_connections: Dict[str, Set[str]] = {}
        
        # Thread subscriptions
        self.thread_subscriptions: Dict[str, Set[str]] = {}
        
        # Project subscriptions
        self.project_subscriptions: Dict[str, Set[str]] = {}
        
        # Agent run subscriptions
        self.agent_subscriptions: Dict[str, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str, user_id: Optional[str] = None):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        self.active_connections[connection_id] = websocket
        
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)
        
        logger.debug(f"WebSocket connection established: {connection_id} (user: {user_id})")
        
        # Send connection confirmation
        await self.send_to_connection(connection_id, {
            "type": "connection_established",
            "connection_id": connection_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    def disconnect(self, connection_id: str, user_id: Optional[str] = None):
        """Remove a WebSocket connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        # Remove from all subscriptions
        self._remove_from_subscriptions(connection_id)
        
        logger.debug(f"WebSocket connection closed: {connection_id}")
    
    def _remove_from_subscriptions(self, connection_id: str):
        """Remove connection from all subscriptions"""
        # Remove from thread subscriptions
        for thread_id in list(self.thread_subscriptions.keys()):
            self.thread_subscriptions[thread_id].discard(connection_id)
            if not self.thread_subscriptions[thread_id]:
                del self.thread_subscriptions[thread_id]
        
        # Remove from project subscriptions
        for project_id in list(self.project_subscriptions.keys()):
            self.project_subscriptions[project_id].discard(connection_id)
            if not self.project_subscriptions[project_id]:
                del self.project_subscriptions[project_id]
        
        # Remove from agent subscriptions
        for agent_id in list(self.agent_subscriptions.keys()):
            self.agent_subscriptions[agent_id].discard(connection_id)
            if not self.agent_subscriptions[agent_id]:
                del self.agent_subscriptions[agent_id]
    
    async def send_to_connection(self, connection_id: str, message: Dict[str, Any]):
        """Send message to a specific connection"""
        if connection_id in self.active_connections:
            try:
                websocket = self.active_connections[connection_id]
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.warning(f"Failed to send message to connection {connection_id}: {e}")
                # Remove broken connection
                if connection_id in self.active_connections:
                    del self.active_connections[connection_id]
                self._remove_from_subscriptions(connection_id)
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Send message to all connections of a specific user"""
        if user_id in self.user_connections:
            connection_ids = list(self.user_connections[user_id])
            for connection_id in connection_ids:
                await self.send_to_connection(connection_id, message)
    
    async def broadcast_to_thread(self, thread_id: str, message: Dict[str, Any], exclude_connection: Optional[str] = None):
        """Broadcast message to all subscribers of a thread"""
        if thread_id in self.thread_subscriptions:
            connection_ids = list(self.thread_subscriptions[thread_id])
            for connection_id in connection_ids:
                if connection_id != exclude_connection:
                    await self.send_to_connection(connection_id, message)
    
    async def broadcast_to_project(self, project_id: str, message: Dict[str, Any], exclude_connection: Optional[str] = None):
        """Broadcast message to all subscribers of a project"""
        if project_id in self.project_subscriptions:
            connection_ids = list(self.project_subscriptions[project_id])
            for connection_id in connection_ids:
                if connection_id != exclude_connection:
                    await self.send_to_connection(connection_id, message)
    
    async def broadcast_to_agent(self, agent_id: str, message: Dict[str, Any], exclude_connection: Optional[str] = None):
        """Broadcast message to all subscribers of an agent"""
        if agent_id in self.agent_subscriptions:
            connection_ids = list(self.agent_subscriptions[agent_id])
            for connection_id in connection_ids:
                if connection_id != exclude_connection:
                    await self.send_to_connection(connection_id, message)
    
    def subscribe_to_thread(self, connection_id: str, thread_id: str):
        """Subscribe a connection to thread updates"""
        if thread_id not in self.thread_subscriptions:
            self.thread_subscriptions[thread_id] = set()
        self.thread_subscriptions[thread_id].add(connection_id)
        logger.debug(f"Connection {connection_id} subscribed to thread {thread_id}")
    
    def subscribe_to_project(self, connection_id: str, project_id: str):
        """Subscribe a connection to project updates"""
        if project_id not in self.project_subscriptions:
            self.project_subscriptions[project_id] = set()
        self.project_subscriptions[project_id].add(connection_id)
        logger.debug(f"Connection {connection_id} subscribed to project {project_id}")
    
    def subscribe_to_agent(self, connection_id: str, agent_id: str):
        """Subscribe a connection to agent updates"""
        if agent_id not in self.agent_subscriptions:
            self.agent_subscriptions[agent_id] = set()
        self.agent_subscriptions[agent_id].add(connection_id)
        logger.debug(f"Connection {connection_id} subscribed to agent {agent_id}")
    
    def unsubscribe_from_thread(self, connection_id: str, thread_id: str):
        """Unsubscribe a connection from thread updates"""
        if thread_id in self.thread_subscriptions:
            self.thread_subscriptions[thread_id].discard(connection_id)
            if not self.thread_subscriptions[thread_id]:
                del self.thread_subscriptions[thread_id]
        logger.debug(f"Connection {connection_id} unsubscribed from thread {thread_id}")
    
    def unsubscribe_from_project(self, connection_id: str, project_id: str):
        """Unsubscribe a connection from project updates"""
        if project_id in self.project_subscriptions:
            self.project_subscriptions[project_id].discard(connection_id)
            if not self.project_subscriptions[project_id]:
                del self.project_subscriptions[project_id]
        logger.debug(f"Connection {connection_id} unsubscribed from project {project_id}")
    
    def unsubscribe_from_agent(self, connection_id: str, agent_id: str):
        """Unsubscribe a connection from agent updates"""
        if agent_id in self.agent_subscriptions:
            self.agent_subscriptions[agent_id].discard(connection_id)
            if not self.agent_subscriptions[agent_id]:
                del self.agent_subscriptions[agent_id]
        logger.debug(f"Connection {connection_id} unsubscribed from agent {agent_id}")
    
    async def handle_message(self, connection_id: str, message: Dict[str, Any]):
        """Handle incoming WebSocket message"""
        try:
            message_type = message.get("type")
            
            if message_type == "subscribe":
                await self._handle_subscribe(connection_id, message)
            elif message_type == "unsubscribe":
                await self._handle_unsubscribe(connection_id, message)
            elif message_type == "ping":
                await self.send_to_connection(connection_id, {
                    "type": "pong",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            await self.send_to_connection(connection_id, {
                "type": "error",
                "message": "Failed to process message"
            })
    
    async def _handle_subscribe(self, connection_id: str, message: Dict[str, Any]):
        """Handle subscription request"""
        resource_type = message.get("resource_type")
        resource_id = message.get("resource_id")
        
        if not resource_type or not resource_id:
            await self.send_to_connection(connection_id, {
                "type": "error",
                "message": "Missing resource_type or resource_id"
            })
            return
        
        if resource_type == "thread":
            self.subscribe_to_thread(connection_id, resource_id)
        elif resource_type == "project":
            self.subscribe_to_project(connection_id, resource_id)
        elif resource_type == "agent":
            self.subscribe_to_agent(connection_id, resource_id)
        else:
            await self.send_to_connection(connection_id, {
                "type": "error",
                "message": f"Unknown resource type: {resource_type}"
            })
            return
        
        await self.send_to_connection(connection_id, {
            "type": "subscribed",
            "resource_type": resource_type,
            "resource_id": resource_id
        })
    
    async def _handle_unsubscribe(self, connection_id: str, message: Dict[str, Any]):
        """Handle unsubscription request"""
        resource_type = message.get("resource_type")
        resource_id = message.get("resource_id")
        
        if not resource_type or not resource_id:
            await self.send_to_connection(connection_id, {
                "type": "error",
                "message": "Missing resource_type or resource_id"
            })
            return
        
        if resource_type == "thread":
            self.unsubscribe_from_thread(connection_id, resource_id)
        elif resource_type == "project":
            self.unsubscribe_from_project(connection_id, resource_id)
        elif resource_type == "agent":
            self.unsubscribe_from_agent(connection_id, resource_id)
        else:
            await self.send_to_connection(connection_id, {
                "type": "error",
                "message": f"Unknown resource type: {resource_type}"
            })
            return
        
        await self.send_to_connection(connection_id, {
            "type": "unsubscribed",
            "resource_type": resource_type,
            "resource_id": resource_id
        })
    
    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return len(self.active_connections)
    
    def get_user_connection_count(self, user_id: str) -> int:
        """Get number of connections for a specific user"""
        return len(self.user_connections.get(user_id, set()))

# Global connection manager instance
connection_manager = ConnectionManager()

# Real-time event helpers
async def notify_message_added(thread_id: str, message_data: Dict[str, Any], exclude_connection: Optional[str] = None):
    """Notify subscribers that a new message was added to a thread"""
    await connection_manager.broadcast_to_thread(thread_id, {
        "type": "message_added",
        "thread_id": thread_id,
        "message": message_data,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }, exclude_connection)

async def notify_thread_updated(thread_id: str, thread_data: Dict[str, Any], exclude_connection: Optional[str] = None):
    """Notify subscribers that a thread was updated"""
    await connection_manager.broadcast_to_thread(thread_id, {
        "type": "thread_updated",
        "thread_id": thread_id,
        "thread": thread_data,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }, exclude_connection)

async def notify_agent_status_changed(agent_id: str, status: str, details: Optional[Dict[str, Any]] = None, exclude_connection: Optional[str] = None):
    """Notify subscribers that an agent's status changed"""
    await connection_manager.broadcast_to_agent(agent_id, {
        "type": "agent_status_changed",
        "agent_id": agent_id,
        "status": status,
        "details": details or {},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }, exclude_connection)

async def notify_project_updated(project_id: str, project_data: Dict[str, Any], exclude_connection: Optional[str] = None):
    """Notify subscribers that a project was updated"""
    await connection_manager.broadcast_to_project(project_id, {
        "type": "project_updated",
        "project_id": project_id,
        "project": project_data,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }, exclude_connection)

async def notify_user(user_id: str, notification_type: str, data: Dict[str, Any]):
    """Send a notification to a specific user"""
    await connection_manager.send_to_user(user_id, {
        "type": "notification",
        "notification_type": notification_type,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })