import json
import logging
from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""

    def __init__(self):
        # Store connections by user_id
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # Store user metadata
        self.user_metadata: Dict[int, Dict] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept and store a new WebSocket connection"""
        await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = []

        self.active_connections[user_id].append(websocket)
        self.user_metadata[user_id] = {
            "connected_at": datetime.utcnow(),
            "subscriptions": ["trades", "positions", "balance", "metrics"],
        }

        logger.info(
            f"User {user_id} connected. Total connections: {len(self.active_connections[user_id])}"
        )

    def disconnect(self, websocket: WebSocket, user_id: int):
        """Remove a WebSocket connection"""
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)

                # Clean up if no more connections for this user
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
                    if user_id in self.user_metadata:
                        del self.user_metadata[user_id]

        logger.info(f"User {user_id} disconnected")

    async def send_personal_message(self, message: Dict, user_id: int):
        """Send message to a specific user"""
        if user_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
                    disconnected.append(connection)

            # Clean up disconnected sockets
            for conn in disconnected:
                self.active_connections[user_id].remove(conn)

    async def broadcast(self, message: Dict):
        """Broadcast message to all connected clients"""
        disconnected_users = []

        for user_id, connections in self.active_connections.items():
            disconnected = []
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to user {user_id}: {e}")
                    disconnected.append(connection)

            # Clean up disconnected sockets
            for conn in disconnected:
                connections.remove(conn)

            if not connections:
                disconnected_users.append(user_id)

        # Clean up users with no connections
        for user_id in disconnected_users:
            del self.active_connections[user_id]
            if user_id in self.user_metadata:
                del self.user_metadata[user_id]

    async def send_trade_update(self, user_id: int, trade_data: Dict):
        """Send trade update to specific user"""
        message = {
            "type": "trade_update",
            "data": trade_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.send_personal_message(message, user_id)

    async def send_position_update(self, user_id: int, position_data: Dict):
        """Send position update to specific user"""
        message = {
            "type": "position_update",
            "data": position_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.send_personal_message(message, user_id)

    async def send_balance_update(self, user_id: int, balance_data: Dict):
        """Send balance update to specific user"""
        message = {
            "type": "balance_update",
            "data": balance_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.send_personal_message(message, user_id)

    async def send_metrics_update(self, user_id: int, metrics_data: Dict):
        """Send metrics update to specific user"""
        message = {
            "type": "metrics_update",
            "data": metrics_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.send_personal_message(message, user_id)

    async def send_performance_update(self, user_id: int, performance_data: Dict):
        """Send performance summary update to specific user"""
        message = {
            "type": "performance_update",
            "data": performance_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.send_personal_message(message, user_id)

    def get_connection_count(self, user_id: int = None) -> int:
        """Get number of active connections"""
        if user_id:
            return len(self.active_connections.get(user_id, []))
        return sum(len(conns) for conns in self.active_connections.values())

    def is_user_connected(self, user_id: int) -> bool:
        """Check if a user has active connections"""
        return (
            user_id in self.active_connections
            and len(self.active_connections[user_id]) > 0
        )


# Global manager instance
manager = ConnectionManager()
