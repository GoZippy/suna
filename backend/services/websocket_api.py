"""
WebSocket API endpoints for real-time communication.
Replaces Supabase real-time functionality.
"""

import json
import uuid
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from services.websocket_manager import connection_manager
from services.auth_middleware import get_user_id_from_token
from utils.logger import logger

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