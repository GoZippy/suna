"""
WebSocket API endpoints for real-time communication.
Replaces Supabase real-time functionality.
"""

import json
import uuid
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException
from services.websocket_manager import connection_manager
from services.auth_middleware import get_user_id_from_token
from utils.logger import logger
from datetime import datetime, timezone, timedelta

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    connection_id: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time communication.
    
    Query parameters:
    - token: JWT token for authentication (optional)
    - connection_id: Custom connection ID (optional, will generate if not provided)
    """
    
    # Generate connection ID if not provided
    if not connection_id:
        connection_id = str(uuid.uuid4())
    
    # Extract user ID from token if provided
    user_id = None
    if token:
        user_id = get_user_id_from_token(token)
    
    try:
        # Accept the WebSocket connection
        await connection_manager.connect(websocket, connection_id, user_id)
        
        logger.info(f"WebSocket connected: {connection_id} (user: {user_id})")
        
        # Handle incoming messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle the message
                await connection_manager.handle_message(connection_id, message)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: {connection_id}")
                break
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from {connection_id}")
                await connection_manager.send_to_connection(connection_id, {
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                logger.error(f"Error handling WebSocket message from {connection_id}: {e}")
                await connection_manager.send_to_connection(connection_id, {
                    "type": "error",
                    "message": "Internal server error"
                })
    
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    
    finally:
        # Clean up connection
        connection_manager.disconnect(connection_id, user_id)

@router.get("/ws/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics"""
    return {
        "total_connections": connection_manager.get_connection_count(),
        "thread_subscriptions": len(connection_manager.thread_subscriptions),
        "project_subscriptions": len(connection_manager.project_subscriptions),
        "agent_subscriptions": len(connection_manager.agent_subscriptions)
    }

@router.post("/ws/broadcast/thread/{thread_id}")
async def broadcast_to_thread(
    thread_id: str,
    message: dict,
    exclude_connection: Optional[str] = None
):
    """
    Broadcast a message to all subscribers of a thread.
    This is an internal API for server-side broadcasting.
    """
    await connection_manager.broadcast_to_thread(thread_id, message, exclude_connection)
    return {"status": "broadcasted", "thread_id": thread_id}

@router.post("/ws/broadcast/project/{project_id}")
async def broadcast_to_project(
    project_id: str,
    message: dict,
    exclude_connection: Optional[str] = None
):
    """
    Broadcast a message to all subscribers of a project.
    This is an internal API for server-side broadcasting.
    """
    await connection_manager.broadcast_to_project(project_id, message, exclude_connection)
    return {"status": "broadcasted", "project_id": project_id}

@router.post("/ws/broadcast/agent/{agent_id}")
async def broadcast_to_agent(
    agent_id: str,
    message: dict,
    exclude_connection: Optional[str] = None
):
    """
    Broadcast a message to all subscribers of an agent.
    This is an internal API for server-side broadcasting.
    """
    await connection_manager.broadcast_to_agent(agent_id, message, exclude_connection)
    return {"status": "broadcasted", "agent_id": agent_id}

@router.post("/ws/notify/user/{user_id}")
async def notify_user(
    user_id: str,
    notification_type: str,
    data: dict
):
    """
    Send a notification to a specific user.
    This is an internal API for server-side notifications.
    """
    from services.websocket_manager import notify_user as ws_notify_user
    await ws_notify_user(user_id, notification_type, data)
    return {"status": "notified", "user_id": user_id}

# Additional endpoints for admin interface

@router.get("/ws/connections")
async def get_connections():
    """Get all WebSocket connections"""
    try:
        # This would typically query the database for persistent connections
        # For now, return active connections from memory
        connections = []
        for connection_id, websocket in connection_manager.active_connections.items():
            # Get user_id from user_connections mapping
            user_id = None
            for uid, conn_ids in connection_manager.user_connections.items():
                if connection_id in conn_ids:
                    user_id = uid
                    break
            
            connections.append({
                "connection_id": connection_id,
                "user_id": user_id,
                "status": "connected",
                "connected_at": datetime.now(timezone.utc).isoformat(),
                "last_activity": datetime.now(timezone.utc).isoformat()
            })
        
        return connections
    except Exception as e:
        logger.error(f"Error getting connections: {e}")
        raise HTTPException(status_code=500, detail="Failed to get connections")

@router.get("/ws/subscriptions")
async def get_subscriptions():
    """Get all active subscriptions"""
    try:
        subscriptions = {
            "threads": [],
            "projects": [],
            "agents": []
        }
        
        # Get thread subscriptions
        for thread_id, connection_ids in connection_manager.thread_subscriptions.items():
            subscriptions["threads"].append({
                "thread_id": thread_id,
                "connections": len(connection_ids)
            })
        
        # Get project subscriptions
        for project_id, connection_ids in connection_manager.project_subscriptions.items():
            subscriptions["projects"].append({
                "project_id": project_id,
                "connections": len(connection_ids)
            })
        
        # Get agent subscriptions
        for agent_id, connection_ids in connection_manager.agent_subscriptions.items():
            subscriptions["agents"].append({
                "agent_id": agent_id,
                "connections": len(connection_ids)
            })
        
        return subscriptions
    except Exception as e:
        logger.error(f"Error getting subscriptions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get subscriptions")

@router.get("/ws/activity")
async def get_recent_activity():
    """Get recent WebSocket activity"""
    try:
        # This would typically query a log table
        # For now, return a sample of recent activity
        activity = [
            {
                "type": "connection_established",
                "description": "New WebSocket connection established",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            {
                "type": "subscription_added",
                "description": "User subscribed to thread updates",
                "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
            }
        ]
        
        return activity
    except Exception as e:
        logger.error(f"Error getting activity: {e}")
        raise HTTPException(status_code=500, detail="Failed to get activity")

@router.post("/ws/connections/{connection_id}/disconnect")
async def disconnect_connection(connection_id: str):
    """Disconnect a specific WebSocket connection"""
    try:
        if connection_id in connection_manager.active_connections:
            # Get user_id for cleanup
            user_id = None
            for uid, conn_ids in connection_manager.user_connections.items():
                if connection_id in conn_ids:
                    user_id = uid
                    break
            
            # Close the WebSocket connection
            websocket = connection_manager.active_connections[connection_id]
            await websocket.close()
            
            # Clean up the connection
            connection_manager.disconnect(connection_id, user_id)
            
            logger.info(f"Admin disconnected WebSocket connection: {connection_id}")
            return {"status": "disconnected", "connection_id": connection_id}
        else:
            raise HTTPException(status_code=404, detail="Connection not found")
    except Exception as e:
        logger.error(f"Error disconnecting connection: {e}")
        raise HTTPException(status_code=500, detail="Failed to disconnect connection")

@router.post("/ws/connections/disconnect-all")
async def disconnect_all_connections():
    """Disconnect all WebSocket connections"""
    try:
        connection_count = len(connection_manager.active_connections)
        
        # Close all connections
        for connection_id, websocket in list(connection_manager.active_connections.items()):
            try:
                await websocket.close()
            except:
                pass
        
        # Clear all connection data
        connection_manager.active_connections.clear()
        connection_manager.user_connections.clear()
        connection_manager.thread_subscriptions.clear()
        connection_manager.project_subscriptions.clear()
        connection_manager.agent_subscriptions.clear()
        
        logger.info(f"Admin disconnected all WebSocket connections: {connection_count} connections")
        return {"status": "disconnected_all", "connection_count": connection_count}
    except Exception as e:
        logger.error(f"Error disconnecting all connections: {e}")
        raise HTTPException(status_code=500, detail="Failed to disconnect all connections")

@router.post("/ws/settings")
async def update_websocket_settings(settings: dict):
    """Update WebSocket configuration settings"""
    try:
        # This would typically update configuration in database or config file
        # For now, just log the settings update
        logger.info(f"WebSocket settings updated: {settings}")
        return {"status": "updated", "settings": settings}
    except Exception as e:
        logger.error(f"Error updating WebSocket settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update settings")

@router.post("/ws/feature-flags")
async def update_feature_flags(flags: dict):
    """Update WebSocket feature flags"""
    try:
        # This would typically update configuration in database or config file
        # For now, just log the feature flags update
        logger.info(f"WebSocket feature flags updated: {flags}")
        return {"status": "updated", "feature_flags": flags}
    except Exception as e:
        logger.error(f"Error updating feature flags: {e}")
        raise HTTPException(status_code=500, detail="Failed to update feature flags")