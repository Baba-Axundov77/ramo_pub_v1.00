# web/routes/websocket_kds.py - KDS Real-time WebSocket Handler
from __future__ import annotations

import json
import asyncio
import threading
import time
from datetime import datetime, timedelta
from collections import defaultdict
from flask import request
from flask_socketio import SocketIO, emit, join_room, leave_room
from src.core.database.connection import get_db

# KDS room
KDS_ROOM = 'kds'

class ConnectionManager:
    """Manages WebSocket connections with TTL cleanup"""
    def __init__(self):
        self.clients = defaultdict(dict)
        self.lock = threading.Lock()
        self._start_cleanup_task()
    
    def add_client(self, client_id, room):
        with self.lock:
            self.clients[room][client_id] = {
                'connected_at': datetime.now(),
                'last_heartbeat': datetime.now()
            }
    
    def remove_client(self, client_id, room):
        with self.lock:
            if client_id in self.clients[room]:
                del self.clients[room][client_id]
    
    def cleanup_expired(self):
        """Clean up expired connections"""
        with self.lock:
            cutoff = datetime.now() - timedelta(minutes=5)
            for room in list(self.clients.keys()):
                expired_clients = [
                    cid for cid, data in self.clients[room].items()
                    if data['last_heartbeat'] < cutoff
                ]
                for cid in expired_clients:
                    del self.clients[room][cid]
                if not self.clients[room]:
                    del self.clients[room]
    
    def _start_cleanup_task(self):
        """Start background cleanup task"""
        def cleanup():
            while True:
                time.sleep(60)  # Cleanup every minute
                self.cleanup_expired()
        
        cleanup_thread = threading.Thread(target=cleanup, daemon=True)
        cleanup_thread.start()
    
    def get_client_count(self, room):
        with self.lock:
            return len(self.clients.get(room, {}))

# Global connection manager
connection_manager = ConnectionManager()
active_orders = {}

def get_socketio():
    """Get SocketIO instance"""
    from src.web.routes.websocket_dashboard import socketio
    return socketio

@get_socketio().on('connect')
def handle_kds_connect():
    """Handle KDS client connection"""
    client_id = request.sid
    
    # Use connection manager
    connection_manager.add_client(client_id, KDS_ROOM)
    
    join_room(KDS_ROOM)
    
    print(f"KDS client {client_id} connected")
    
    # Send active orders to new client
    emit('kds_orders_update', {
        'type': 'initial_orders',
        'orders': list(active_orders.values())
    }, room=client_id)
    
    # Broadcast client count
    emit('kds_client_count', {'count': connection_manager.get_client_count(KDS_ROOM)}, room=KDS_ROOM)

@get_socketio().on('disconnect')
def handle_kds_disconnect():
    """Handle KDS client disconnection"""
    client_id = request.sid
    
    # Use connection manager
    connection_manager.remove_client(client_id, KDS_ROOM)
    leave_room(KDS_ROOM)
    print(f"KDS client {client_id} disconnected")
    
    emit('kds_client_count', {'count': connection_manager.get_client_count(KDS_ROOM)}, room=KDS_ROOM)

@get_socketio().on('order_ready')
def handle_order_ready(data):
    """Handle order ready notification with analytics logging"""
    client_id = request.sid
    order_id = data.get('order_id')
    table_number = data.get('table_number')
    waiter_name = data.get('waiter_name')
    completion_time = data.get('completion_time', 0)  # in seconds
    
    if not order_id:
        emit('error', {'message': 'Order ID required'})
        return
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Update order status in database
        cursor.execute("""
            UPDATE orders 
            SET status = 'ready', completed_at = %s 
            WHERE id = %s
        """, (datetime.now(), order_id))
        
        # Log analytics data
        cursor.execute("""
            INSERT INTO order_analytics 
            (order_id, table_number, waiter_name, start_time, end_time, completion_time, created_at)
            SELECT %s, %s, %s, created_at, %s, %s, %s
            FROM orders WHERE id = %s
        """, (order_id, table_number, waiter_name, datetime.now(), completion_time, datetime.now(), order_id))
        
        db.commit()
        cursor.close()
        
        # Remove from active orders
        if order_id in active_orders:
            del active_orders[order_id]
        
        # Send notification to waiter's mobile device
        waiter_notification = {
            'type': 'order_ready',
            'order_id': order_id,
            'table_number': table_number,
            'waiter_name': waiter_name,
            'message': f'Masa {table_number} - Sifariş Hazırdır!',
            'timestamp': datetime.now().isoformat()
        }
        
        # Send to waiter's room (assuming waiter_id is available)
        waiter_room = f"waiter_{waiter_name}"  # Simplified - in real app, use waiter_id
        emit('luxury_notification', waiter_notification, room=waiter_room)
        
        # Broadcast to all KDS clients
        emit('kds_orders_update', {
            'type': 'order_removed',
            'order_id': order_id
        }, room=KDS_ROOM)
        
        # Send to dashboard for statistics
        emit('dashboard_update', {
            'type': 'order_completed',
            'order_id': order_id,
            'table_number': table_number,
            'completion_time': completion_time
        }, room='dashboard')
        
        print(f"Order {order_id} marked as ready for table {table_number} (completed in {completion_time}s)")
        
    except Exception as e:
        emit('error', {'message': f'Error marking order ready: {str(e)}'})

@get_socketio().on('order_analytics')
def handle_order_analytics(data):
    """Handle order analytics data from KDS"""
    client_id = request.sid
    analytics_data = data.get('data')
    
    if not analytics_data:
        emit('error', {'message': 'Analytics data required'})
        return
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Insert analytics data
        cursor.execute("""
            INSERT INTO order_analytics 
            (order_id, table_number, start_time, end_time, completion_time, items_count, priority, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            analytics_data.get('order_id'),
            analytics_data.get('table_number'),
            analytics_data.get('start_time'),
            analytics_data.get('end_time'),
            analytics_data.get('completion_time'),
            analytics_data.get('items_count'),
            analytics_data.get('priority'),
            analytics_data.get('timestamp')
        ))
        
        db.commit()
        cursor.close()
        
        print(f"Analytics logged for order {analytics_data.get('order_id')}")
        
    except Exception as e:
        print(f"Error logging analytics: {e}")
        emit('error', {'message': f'Error logging analytics: {str(e)}'})

@get_socketio().on('return_all_orders')
def handle_return_all_orders():
    """Handle return all orders to queue"""
    client_id = request.sid
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get all ready orders from last hour
        cursor.execute("""
            SELECT o.id, o.table_id, o.status, o.created_at, o.completed_at,
                   t.number as table_number, u.full_name as waiter_name
            FROM orders o
            JOIN tables t ON o.table_id = t.id
            LEFT JOIN users u ON o.waiter_id = u.id
            WHERE o.status = 'ready' 
            AND o.completed_at > %s
            ORDER BY o.completed_at DESC
        """, (datetime.now() - timedelta(hours=1),))
        
        orders = cursor.fetchall()
        cursor.close()
        
        returned_orders = []
        for order in orders:
            order_data = {
                'id': order[0],
                'table_id': order[1],
                'table_number': order[5],
                'waiter_name': order[6] or 'Unknown',
                'status': 'new',  # Reset to new status
                'created_at': order[3].isoformat(),
                'items': [],  # Would need to fetch order items
                'notes': '',
                'priority': False
            }
            
            # Update database
            cursor = db.cursor()
            cursor.execute("""
                UPDATE orders 
                SET status = 'pending', completed_at = NULL 
                WHERE id = %s
            """, (order_data['id'],))
            db.commit()
            cursor.close()
            
            # Add back to active orders
            active_orders[order_data['id']] = order_data
            returned_orders.append(order_data)
        
        # Broadcast to KDS
        emit('kds_orders_update', {
            'type': 'orders_returned',
            'orders': returned_orders
        }, room=KDS_ROOM)
        
        print(f"Returned {len(returned_orders)} orders to queue")
        
    except Exception as e:
        emit('error', {'message': f'Error returning orders: {str(e)}'})

@get_socketio().on('print_orders')
def handle_print_orders():
    """Handle print orders request"""
    client_id = request.sid
    
    try:
        # Get current active orders for printing
        current_orders = list(active_orders.values())
        
        # In a real implementation, this would:
        # 1. Generate print-ready HTML/PDF
        # 2. Send to kitchen printer
        # 3. Log print job
        
        print_data = {
            'type': 'print_job',
            'orders': current_orders,
            'timestamp': datetime.now().isoformat(),
            'kds_client': client_id
        }
        
        # For demo, just log the print job
        print(f"Print job initiated for {len(current_orders)} orders")
        
        emit('kds_print_status', {
            'status': 'success',
            'message': f'{len(current_orders)} sifariş çap olundu'
        }, room=client_id)
        
    except Exception as e:
        emit('error', {'message': f'Error printing orders: {str(e)}'})

# External functions for other modules
def broadcast_new_order(order_data):
    """Broadcast new order to KDS"""
    order_id = order_data.get('id')
    
    # Determine priority
    is_priority = False
    
    # VIP tables get priority
    if order_data.get('table_number') in [1, 2, 3, 4]:  # Assuming VIP tables
        is_priority = True
    
    # Drinks-only orders get priority
    items = order_data.get('items', [])
    if all(item.get('category') == 'drinks' for item in items):
        is_priority = True
    
    order_data['priority'] = is_priority
    
    # Add to active orders
    active_orders[order_id] = order_data
    
    # Broadcast to KDS
    socketio = get_socketio()
    socketio.emit('kds_orders_update', {
        'type': 'new_order',
        'order': order_data
    }, room=KDS_ROOM)
    
    print(f"New order {order_id} broadcasted to KDS (priority: {is_priority})")

def broadcast_order_update(order_id, update_data):
    """Broadcast order update to KDS"""
    if order_id in active_orders:
        active_orders[order_id].update(update_data)
        
        socketio = get_socketio()
        socketio.emit('kds_orders_update', {
            'type': 'order_updated',
            'order_id': order_id,
            'updates': update_data
        }, room=KDS_ROOM)

def broadcast_order_cancelled(order_id):
    """Broadcast order cancellation to KDS"""
    if order_id in active_orders:
        del active_orders[order_id]
        
        socketio = get_socketio()
        socketio.emit('kds_orders_update', {
            'type': 'order_cancelled',
            'order_id': order_id
        }, room=KDS_ROOM)
        
        print(f"Order {order_id} cancelled and removed from KDS")

def get_active_orders():
    """Get current active orders"""
    return list(active_orders.values())

def get_kds_stats():
    """Get KDS statistics"""
    total_orders = len(active_orders)
    waiting_orders = len([o for o in active_orders.values() 
                        if (datetime.now() - datetime.fromisoformat(o['created_at'])).total_seconds() > 300])  # > 5 minutes
    delayed_orders = len([o for o in active_orders.values() 
                          if (datetime.now() - datetime.fromisoformat(o['created_at'])).total_seconds() > 900])  # > 15 minutes
    
    return {
        'total_orders': total_orders,
        'waiting_orders': waiting_orders,
        'delayed_orders': delayed_orders,
        'priority_orders': len([o for o in active_orders.values() if o.get('priority')])
    }

# Background task to clean up old orders
def cleanup_old_orders():
    """Clean up orders older than 24 hours"""
    current_time = datetime.now()
    cutoff_time = current_time - timedelta(hours=24)
    
    old_orders = []
    for order_id, order in list(active_orders.items()):
        order_time = datetime.fromisoformat(order['created_at'])
        if order_time < cutoff_time:
            old_orders.append(order_id)
            del active_orders[order_id]
    
    if old_orders:
        socketio = get_socketio()
        socketio.emit('kds_orders_update', {
            'type': 'orders_cleaned',
            'order_ids': old_orders
        }, room=KDS_ROOM)
        
        print(f"Cleaned up {len(old_orders)} old orders from KDS")
    
    return old_orders

# Periodic cleanup task
def start_kds_cleanup_tasks():
    """Start background cleanup tasks for KDS"""
    import threading
    import time
    
    def cleanup_loop():
        while True:
            try:
                cleanup_old_orders()
                time.sleep(3600)  # Run every hour
            except Exception as e:
                print(f"KDS cleanup task error: {e}")
                time.sleep(3600)
    
    cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
    cleanup_thread.start()
    print("Started KDS cleanup tasks")

__all__ = [
    'broadcast_new_order',
    'broadcast_order_update', 
    'broadcast_order_cancelled',
    'get_active_orders',
    'get_kds_stats'
]
