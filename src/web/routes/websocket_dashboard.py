# web/routes/websocket_dashboard.py - Real-time Dashboard WebSocket Handler
from __future__ import annotations

import json
import asyncio
from datetime import datetime
from flask import Blueprint, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from src.core.database.connection import get_db

# Create WebSocket blueprint
ws_bp = Blueprint('websocket_dashboard', __name__)

# Initialize SocketIO
socketio = SocketIO(cors_allowed_origins="*", async_mode='thread')

# Dashboard room for broadcasting updates
DASHBOARD_ROOM = 'dashboard'

# Connected clients tracking
connected_clients = set()

@socketio.on('connect')
def handle_connect():
    """Handle client connection to dashboard WebSocket"""
    client_id = request.sid
    connected_clients.add(client_id)
    join_room(DASHBOARD_ROOM)
    
    print(f"Client {client_id} connected to dashboard")
    
    # Send initial data
    emit('connected', {
        'message': 'Connected to Ramo Pub Dashboard',
        'client_id': client_id,
        'timestamp': datetime.now().isoformat()
    })
    
    # Broadcast client count
    emit('client_count', {'count': len(connected_clients)}, room=DASHBOARD_ROOM)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    client_id = request.sid
    connected_clients.discard(client_id)
    leave_room(DASHBOARD_ROOM)
    
    print(f"Client {client_id} disconnected from dashboard")
    
    # Broadcast updated client count
    emit('client_count', {'count': len(connected_clients)}, room=DASHBOARD_ROOM)

@socketio.on('join_dashboard')
def handle_join_dashboard():
    """Explicitly join dashboard room"""
    join_room(DASHBOARD_ROOM)
    emit('joined', {'message': 'Joined dashboard room'})

def broadcast_new_order(order_data):
    """Broadcast new order to all dashboard clients"""
    try:
        # Calculate updated stats
        db = get_db()
        cursor = db.cursor()
        
        # Get current active orders count
        cursor.execute("""
            SELECT COUNT(*) as active_orders,
                   COALESCE(SUM(total_amount), 0) as total_revenue
            FROM orders 
            WHERE status IN ('pending', 'preparing')
        """)
        order_stats = cursor.fetchone()
        
        # Get current revenue
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) as revenue
            FROM payments 
            WHERE DATE(created_at) = CURRENT_DATE
            AND status = 'completed'
        """)
        revenue_data = cursor.fetchone()
        
        cursor.close()
        
        broadcast_data = {
            'type': 'new_order',
            'order_id': order_data.get('id'),
            'table_id': order_data.get('table_id'),
            'total_amount': order_data.get('total_amount'),
            'active_orders': order_stats.active_orders,
            'total_revenue': float(revenue_data.revenue) + float(order_data.get('total_amount', 0)),
            'timestamp': datetime.now().isoformat()
        }
        
        socketio.emit('dashboard_update', broadcast_data, room=DASHBOARD_ROOM)
        print(f"Broadcasted new order: {order_data.get('id')}")
        
    except Exception as e:
        print(f"Error broadcasting new order: {e}")

def broadcast_table_status(table_data):
    """Broadcast table status changes"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get current table statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'occupied' THEN 1 ELSE 0 END) as occupied,
                SUM(CASE WHEN status = 'available' THEN 1 ELSE 0 END) as available,
                SUM(CASE WHEN status = 'reserved' THEN 1 ELSE 0 END) as reserved
            FROM tables
        """)
        table_stats = cursor.fetchone()
        
        # Get all table details
        cursor.execute("""
            SELECT id, number, name, status
            FROM tables
            ORDER BY number
        """)
        tables = cursor.fetchall()
        
        cursor.close()
        
        broadcast_data = {
            'type': 'table_status',
            'table_id': table_data.get('id'),
            'table_number': table_data.get('number'),
            'new_status': table_data.get('status'),
            'occupied_tables': table_stats.occupied,
            'available_tables': table_stats.available,
            'reserved_tables': table_stats.reserved,
            'tables': [
                {
                    'id': t[0],
                    'number': t[1],
                    'name': t[2],
                    'status': t[3]
                } for t in tables
            ],
            'timestamp': datetime.now().isoformat()
        }
        
        socketio.emit('dashboard_update', broadcast_data, room=DASHBOARD_ROOM)
        print(f"Broadcasted table status: Table {table_data.get('number')} -> {table_data.get('status')}")
        
    except Exception as e:
        print(f"Error broadcasting table status: {e}")

def broadcast_payment_completed(payment_data):
    """Broadcast payment completion"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get updated revenue
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) as revenue,
                   COUNT(*) as payment_count
            FROM payments 
            WHERE DATE(created_at) = CURRENT_DATE
            AND status = 'completed'
        """)
        revenue_stats = cursor.fetchone()
        
        # Get active orders
        cursor.execute("""
            SELECT COUNT(*) as active_orders,
                   COALESCE(SUM(total_amount), 0) as total_revenue
            FROM orders 
            WHERE status IN ('pending', 'preparing')
        """)
        order_stats = cursor.fetchone()
        
        cursor.close()
        
        broadcast_data = {
            'type': 'payment_completed',
            'payment_id': payment_data.get('id'),
            'order_id': payment_data.get('order_id'),
            'amount': payment_data.get('amount'),
            'total_revenue': float(revenue_stats.revenue),
            'payment_count': revenue_stats.payment_count,
            'active_orders': order_stats.active_orders,
            'timestamp': datetime.now().isoformat()
        }
        
        socketio.emit('dashboard_update', broadcast_data, room=DASHBOARD_ROOM)
        print(f"Broadcasted payment completion: {payment_data.get('id')} - {payment_data.get('amount')}₼")
        
    except Exception as e:
        print(f"Error broadcasting payment completion: {e}")

def broadcast_staff_status(staff_data):
    """Broadcast staff status changes"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get staff statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_staff,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as online_staff
            FROM staff
        """)
        staff_stats = cursor.fetchone()
        
        cursor.close()
        
        broadcast_data = {
            'type': 'staff_status',
            'staff_id': staff_data.get('id'),
            'staff_name': staff_data.get('name'),
            'is_active': staff_data.get('is_active'),
            'online_staff': staff_stats.online_staff,
            'total_staff': staff_stats.total_staff,
            'timestamp': datetime.now().isoformat()
        }
        
        socketio.emit('dashboard_update', broadcast_data, room=DASHBOARD_ROOM)
        print(f"Broadcasted staff status: {staff_data.get('name')} -> {'Online' if staff_data.get('is_active') else 'Offline'}")
        
    except Exception as e:
        print(f"Error broadcasting staff status: {e}")

@socketio.on('request_stats')
def handle_request_stats():
    """Handle client request for current stats"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get current dashboard stats
        cursor.execute("""
            SELECT 
                (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE DATE(created_at) = CURRENT_DATE AND status = 'completed') as revenue,
                (SELECT COUNT(*) FROM tables WHERE status = 'occupied') as occupied_tables,
                (SELECT COUNT(*) FROM orders WHERE status IN ('pending', 'preparing')) as active_orders,
                (SELECT SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) FROM staff) as online_staff
        """)
        stats = cursor.fetchone()
        
        cursor.close()
        
        response_data = {
            'type': 'stats_update',
            'revenue': float(stats.revenue),
            'occupied_tables': stats.occupied_tables,
            'active_orders': stats.active_orders,
            'online_staff': stats.online_staff,
            'timestamp': datetime.now().isoformat()
        }
        
        emit('dashboard_update', response_data)
        
    except Exception as e:
        print(f"Error handling stats request: {e}")
        emit('error', {'message': 'Failed to load stats'})

@socketio.on('ping')
def handle_ping():
    """Handle ping for connection health check"""
    emit('pong', {'timestamp': datetime.now().isoformat()})

# Helper functions to be called from other parts of the application
def notify_dashboard(event_type, data):
    """Generic dashboard notification function"""
    broadcast_functions = {
        'new_order': broadcast_new_order,
        'table_status': broadcast_table_status,
        'payment_completed': broadcast_payment_completed,
        'staff_status': broadcast_staff_status
    }
    
    broadcast_func = broadcast_functions.get(event_type)
    if broadcast_func:
        broadcast_func(data)
    else:
        print(f"Unknown dashboard event type: {event_type}")

def get_connected_clients_count():
    """Get number of connected dashboard clients"""
    return len(connected_clients)

# Export socketio instance for app initialization
__all__ = ['socketio', 'ws_bp', 'notify_dashboard', 'get_connected_clients_count']
