"""
WebSocket Connection Manager - Safe connection handling with TTL and cleanup
Prevents memory leaks and ensures proper client management
"""

import json
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class WebSocketConnectionManager:
    """
    Thread-safe WebSocket connection manager with automatic cleanup
    """
    
    def __init__(self, cleanup_interval: int = 300):
        self.connected_clients = defaultdict(dict)
        self.connection_lock = threading.Lock()
        self.cleanup_interval = cleanup_interval  # 5 minutes default
        self._start_cleanup_task()
        
    def add_client(self, client_id: str, room: str, user_data: Dict[str, Any]) -> None:
        """Add client to room with timestamp"""
        with self.connection_lock:
            self.connected_clients[room][client_id] = {
                **user_data,
                'connected_at': datetime.now(),
                'last_heartbeat': datetime.now(),
                'room': room
            }
            logger.info(f"Client {client_id} added to room {room}")
            
    def remove_client(self, client_id: str, room: str) -> None:
        """Remove client from room"""
        with self.connection_lock:
            if room in self.connected_clients and client_id in self.connected_clients[room]:
                del self.connected_clients[room][client_id]
                logger.info(f"Client {client_id} removed from room {room}")
                
    def update_heartbeat(self, client_id: str, room: str) -> None:
        """Update client heartbeat timestamp"""
        with self.connection_lock:
            if room in self.connected_clients and client_id in self.connected_clients[room]:
                self.connected_clients[room][client_id]['last_heartbeat'] = datetime.now()
                
    def get_room_clients(self, room: str) -> Dict[str, Dict[str, Any]]:
        """Get all clients in a room"""
        with self.connection_lock:
            return dict(self.connected_clients.get(room, {}))
            
    def get_client_count(self, room: str) -> int:
        """Get number of clients in a room"""
        with self.connection_lock:
            return len(self.connected_clients.get(room, {}))
            
    def cleanup_expired_clients(self) -> None:
        """Remove expired clients based on heartbeat"""
        cutoff_time = datetime.now() - timedelta(seconds=self.cleanup_interval)
        cleaned_count = 0
        
        with self.connection_lock:
            for room in list(self.connected_clients.keys()):
                expired_clients = []
                for client_id, client_data in self.connected_clients[room].items():
                    if client_data['last_heartbeat'] < cutoff_time:
                        expired_clients.append(client_id)
                        
                for client_id in expired_clients:
                    del self.connected_clients[room][client_id]
                    cleaned_count += 1
                    
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} expired WebSocket clients")
            
    def _start_cleanup_task(self) -> None:
        """Start background cleanup task"""
        def cleanup_loop():
            while True:
                try:
                    self.cleanup_expired_clients()
                    asyncio.sleep(60)  # Check every minute
                except Exception as e:
                    logger.error(f"WebSocket cleanup error: {e}")
                    
        cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        cleanup_thread.start()
        logger.info("WebSocket cleanup task started")

# Global connection manager instances
tables_manager = WebSocketConnectionManager()
kds_manager = WebSocketConnectionManager()
dashboard_manager = WebSocketConnectionManager()

def get_manager_for_room(room: str) -> WebSocketConnectionManager:
    """Get appropriate manager for room type"""
    if room.startswith('tables'):
        return tables_manager
    elif room.startswith('kds'):
        return kds_manager
    elif room.startswith('dashboard'):
        return dashboard_manager
    else:
        return tables_manager  # default
