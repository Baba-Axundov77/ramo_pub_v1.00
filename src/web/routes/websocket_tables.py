# web/routes/websocket_tables.py - Real-time Table Management WebSocket Handler
from __future__ import annotations

import json
import asyncio
from datetime import datetime, timedelta
from flask import request
from flask_socketio import SocketIO, emit, join_room, leave_room
from src.core.database.connection import get_db

# Table management room
TABLES_ROOM = 'tables'

# Connected clients tracking
connected_clients = {}
table_locks = {}  # table_id -> {user, user_name, timestamp}

def get_socketio():
    """Get SocketIO instance"""
    from src.web.routes.websocket_dashboard import socketio
    return socketio

@get_socketio().on('connect')
def handle_connect_tables():
    """Handle client connection to tables WebSocket"""
    client_id = request.sid
    user_name = getattr(request, 'user', {}).get('full_name', 'Anonymous')
    
    connected_clients[client_id] = {
        'user': user_name,
        'connected_at': datetime.now(),
        'room': TABLES_ROOM
    }
    
    join_room(TABLES_ROOM)
    
    print(f"Client {client_id} ({user_name}) connected to tables")
    
    # Send current table locks
    emit('table_locks_update', {
        'type': 'locks_status',
        'locks': table_locks
    })
    
    # Broadcast client count
    emit('tables_client_count', {'count': len(connected_clients)}, room=TABLES_ROOM)

@get_socketio().on('disconnect')
def handle_disconnect_tables():
    """Handle client disconnection"""
    client_id = request.sid
    
    if client_id in connected_clients:
        client_info = connected_clients[client_id]
        user_name = client_info['user']
        
        # Release all locks held by this user
        tables_to_unlock = []
        for table_id, lock_info in list(table_locks.items()):
            if lock_info['user'] == user_name:
                tables_to_unlock.append(table_id)
                del table_locks[table_id]
        
        # Broadcast table unlocks
        for table_id in tables_to_unlock:
            emit('tables_update', {
                'type': 'table_unlocked',
                'table_id': table_id,
                'user': user_name
            }, room=TABLES_ROOM)
        
        del connected_clients[client_id]
        leave_room(TABLES_ROOM)
        
        print(f"Client {client_id} ({user_name}) disconnected from tables")
        print(f"Released locks for tables: {tables_to_unlock}")
    
    # Broadcast updated client count
    emit('tables_client_count', {'count': len(connected_clients)}, room=TABLES_ROOM)

@get_socketio().on('lock_table')
def handle_lock_table(data):
    """Handle table locking request"""
    client_id = request.sid
    user_name = data.get('user_name', 'Anonymous')
    table_id = data.get('table_id')
    
    if not table_id:
        emit('error', {'message': 'Table ID required'})
        return
    
    # Check if table is already locked
    if table_id in table_locks:
        existing_lock = table_locks[table_id]
        if existing_lock['user'] != user_name:
            emit('tables_update', {
                'type': 'table_locked',
                'table_id': table_id,
                'user': existing_lock['user'],
                'user_name': existing_lock['user_name'],
                'already_locked': True
            })
            return
        else:
            # User already has the lock, update timestamp
            table_locks[table_id]['timestamp'] = datetime.now()
    else:
        # Lock the table
        table_locks[table_id] = {
            'user': user_name,
            'user_name': user_name,
            'timestamp': datetime.now(),
            'client_id': client_id
        }
        
        print(f"Table {table_id} locked by {user_name}")
    
    # Broadcast the lock
    emit('tables_update', {
        'type': 'table_locked',
        'table_id': table_id,
        'user': user_name,
        'user_name': user_name,
        'already_locked': False
    }, room=TABLES_ROOM)

@get_socketio().on('unlock_table')
def handle_unlock_table(data):
    """Handle table unlocking request"""
    client_id = request.sid
    user_name = data.get('user', 'Anonymous')
    table_id = data.get('table_id')
    
    if not table_id:
        emit('error', {'message': 'Table ID required'})
        return
    
    # Check if user has the lock
    if table_id in table_locks:
        lock_info = table_locks[table_id]
        if lock_info['user'] == user_name:
            del table_locks[table_id]
            
            print(f"Table {table_id} unlocked by {user_name}")
            
            # Broadcast the unlock
            emit('tables_update', {
                'type': 'table_unlocked',
                'table_id': table_id,
                'user': user_name
            }, room=TABLES_ROOM)
        else:
            emit('error', {'message': 'You do not have the lock for this table'})
    else:
        emit('error', {'message': 'Table is not locked'})

@get_socketio().on('heartbeat')
def handle_heartbeat(data):
    """Handle heartbeat for maintaining locks"""
    client_id = request.sid
    user_name = data.get('user', 'Anonymous')
    
    # Update client heartbeat
    if client_id in connected_clients:
        connected_clients[client_id]['last_heartbeat'] = datetime.now()
    
    # Extend lock timeout for user's locked tables
    current_time = datetime.now()
    for table_id, lock_info in list(table_locks.items()):
        if lock_info['user'] == user_name:
            lock_info['timestamp'] = current_time

@get_socketio().on('request_table_status')
def handle_request_table_status(data):
    """Handle request for current table status"""
    table_id = data.get('table_id')
    
    if not table_id:
        emit('error', {'message': 'Table ID required'})
        return
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get table information
        cursor.execute("""
            SELECT t.id, t.number, t.name, t.status, t.zone,
                   o.id as order_id, o.total_amount, o.created_at as order_created_at,
                   u.full_name as waiter_name
            FROM tables t
            LEFT JOIN orders o ON t.id = o.table_id AND o.status IN ('pending', 'preparing')
            LEFT JOIN users u ON o.waiter_id = u.id
            WHERE t.id = %s
        """, (table_id,))
        
        table_data = cursor.fetchone()
        cursor.close()
        
        if table_data:
            response = {
                'type': 'table_status_response',
                'table_id': table_id,
                'status': table_data[3],
                'zone': table_data[4],
                'current_order': None
            }
            
            if table_data[5]:  # Has active order
                response['current_order'] = {
                    'id': table_data[5],
                    'total_amount': float(table_data[6]),
                    'created_at': table_data[7].isoformat(),
                    'waiter_name': table_data[8] or 'Unknown'
                }
            
            # Add lock information
            if table_id in table_locks:
                response['locked_by'] = table_locks[table_id]['user_name']
            
            emit('tables_update', response)
        else:
            emit('error', {'message': 'Table not found'})
            
    except Exception as e:
        emit('error', {'message': f'Error fetching table status: {str(e)}'})

@get_socketio().on('update_table_status')
def handle_update_table_status(data):
    """Handle table status update"""
    client_id = request.sid
    user_name = data.get('user', 'Anonymous')
    table_id = data.get('table_id')
    new_status = data.get('status')
    
    if not table_id or not new_status:
        emit('error', {'message': 'Table ID and status required'})
        return
    
    # Check if user has the lock
    if table_id in table_locks and table_locks[table_id]['user'] != user_name:
        emit('error', {'message': 'You do not have permission to update this table'})
        return
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Update table status
        cursor.execute("""
            UPDATE tables 
            SET status = %s, updated_at = %s 
            WHERE id = %s
        """, (new_status, datetime.now(), table_id))
        
        db.commit()
        cursor.close()
        
        print(f"Table {table_id} status updated to {new_status} by {user_name}")
        
        # Broadcast the update
        emit('tables_update', {
            'type': 'table_status_changed',
            'table_id': table_id,
            'status': new_status,
            'updated_by': user_name,
            'timestamp': datetime.now().isoformat()
        }, room=TABLES_ROOM)
        
    except Exception as e:
        emit('error', {'message': f'Error updating table status: {str(e)}'})

# Background task to clean up expired locks
def cleanup_expired_locks():
    """Clean up locks that have expired (no heartbeat for 2 minutes)"""
    current_time = datetime.now()
    expired_locks = []
    
    for table_id, lock_info in list(table_locks.items()):
        # Check if lock is older than 2 minutes
        if current_time - lock_info['timestamp'] > timedelta(minutes=2):
            expired_locks.append(table_id)
            del table_locks[table_id]
            
            print(f"Expired lock for table {table_id} (user: {lock_info['user_name']})")
            
            # Broadcast the unlock
            get_socketio().emit('tables_update', {
                'type': 'table_unlocked',
                'table_id': table_id,
                'user': lock_info['user'],
                'reason': 'expired'
            }, room=TABLES_ROOM)
    
    return expired_locks

# Background task to clean up disconnected clients
def cleanup_disconnected_clients():
    """Clean up clients that haven't sent heartbeat in 5 minutes"""
    current_time = datetime.now()
    disconnected_clients = []
    
    for client_id, client_info in list(connected_clients.items()):
        last_heartbeat = client_info.get('last_heartbeat', client_info['connected_at'])
        if current_time - last_heartbeat > timedelta(minutes=5):
            disconnected_clients.append(client_id)
            
            # Release locks for this client
            tables_to_unlock = []
            for table_id, lock_info in list(table_locks.items()):
                if lock_info['user'] == client_info['user']:
                    tables_to_unlock.append(table_id)
                    del table_locks[table_id]
            
            # Broadcast unlocks
            for table_id in tables_to_unlock:
                get_socketio().emit('tables_update', {
                    'type': 'table_unlocked',
                    'table_id': table_id,
                    'user': client_info['user'],
                    'reason': 'disconnected'
                }, room=TABLES_ROOM)
            
            del connected_clients[client_id]
            print(f"Cleaned up disconnected client: {client_id} ({client_info['user']})")
    
    return disconnected_clients

# Helper functions for external use
def broadcast_table_update(table_id, status, details=None):
    """Broadcast table status update to all connected clients"""
    get_socketio().emit('tables_update', {
        'type': 'table_status_changed',
        'table_id': table_id,
        'status': status,
        'details': details or {},
        'timestamp': datetime.now().isoformat()
    }, room=TABLES_ROOM)

def broadcast_new_order(table_id, order_data):
    """Broadcast new order to table"""
    get_socketio().emit('tables_update', {
        'type': 'new_order',
        'table_id': table_id,
        'order': order_data,
        'timestamp': datetime.now().isoformat()
    }, room=TABLES_ROOM)

def broadcast_table_waiting(table_id, waiting_type='service'):
    """Broadcast that table needs service"""
    get_socketio().emit('tables_update', {
        'type': 'table_waiting',
        'table_id': table_id,
        'waiting_type': waiting_type,
        'timestamp': datetime.now().isoformat()
    }, room=TABLES_ROOM)

def get_table_locks():
    """Get current table locks"""
    return table_locks.copy()

def get_connected_clients_count():
    """Get number of connected clients"""
    return len(connected_clients)

# Periodic cleanup task
def start_cleanup_tasks():
    """Start background cleanup tasks"""
    import threading
    import time
    
    def cleanup_loop():
        while True:
            try:
                cleanup_expired_locks()
                cleanup_disconnected_clients()
                time.sleep(30)  # Run every 30 seconds
            except Exception as e:
                print(f"Cleanup task error: {e}")
                time.sleep(30)
    
    cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
    cleanup_thread.start()
    print("Started table management cleanup tasks")

# Initialize cleanup tasks when module is imported
start_cleanup_tasks()

__all__ = [
    'broadcast_table_update', 
    'broadcast_new_order', 
    'broadcast_table_waiting',
    'get_table_locks',
    'get_connected_clients_count'
]
