# web/routes/websocket_admin.py - Admin Analytics WebSocket Handler
from __future__ import annotations

import json
import asyncio
import time
import threading
from datetime import datetime, timedelta
from flask import request, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from functools import wraps

# Admin room
ADMIN_ROOM = 'admin'

# Connected admin clients
admin_clients = {}

# Simple cache implementation with lock for stampede protection
class SimpleCache:
    def __init__(self):
        self.cache = {}
        self.locks = {}
        self.lock = threading.Lock()
    
    def get(self, key, default=None):
        with self.lock:
            item = self.cache.get(key)
            if item and item['expires'] > datetime.now():
                return item['value']
            return default
    
    def set(self, key, value, ex=None):
        with self.lock:
            expires = datetime.now() + timedelta(seconds=ex) if ex else None
            self.cache[key] = {'value': value, 'expires': expires}
    
    def set_nx(self, key, value, ex=None):
        with self.lock:
            if key not in self.cache:
                expires = datetime.now() + timedelta(seconds=ex) if ex else None
                self.cache[key] = {'value': value, 'expires': expires}
                return True
            return False
    
    def delete(self, key):
        with self.lock:
            self.cache.pop(key, None)

analytics_cache = SimpleCache()

def get_socketio():
    """Get SocketIO instance"""
    from src.web.routes.websocket_dashboard import socketio
    return socketio

def require_admin_role(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user has admin role
        user_role = session.get('user_role', 'user')
        if user_role != 'admin':
            emit('error', {'message': 'Admin access required'})
            return
        return f(*args, **kwargs)
    return decorated_function

@get_socketio().on('connect')
@require_admin_role
def handle_admin_connect():
    """Handle admin client connection"""
    client_id = request.sid
    user_id = session.get('user_id')
    user_name = session.get('user_name', 'Unknown')
    
    admin_clients[client_id] = {
        'connected_at': datetime.now(),
        'user_id': user_id,
        'user_name': user_name,
        'room': ADMIN_ROOM
    }
    
    join_room(ADMIN_ROOM)
    
    print(f"Admin {user_name} ({client_id}) connected")
    
    # Send initial data to new admin
    emit('admin_initial_data', {
        'type': 'initial_data',
        'kpi_data': get_cached_kpi_data(),
        'analytics': get_cached_analytics(),
        'last_update': datetime.now().isoformat()
    }, room=client_id)
    
    # Broadcast client count
    emit('admin_client_count', {'count': len(admin_clients)}, room=ADMIN_ROOM)

@get_socketio().on('disconnect')
def handle_admin_disconnect():
    """Handle admin client disconnection"""
    client_id = request.sid
    
    if client_id in admin_clients:
        user_name = admin_clients[client_id].get('user_name', 'Unknown')
        del admin_clients[client_id]
        leave_room(ADMIN_ROOM)
        print(f"Admin {user_name} ({client_id}) disconnected")
    
    emit('admin_client_count', {'count': len(admin_clients)}, room=ADMIN_ROOM)

@get_socketio().on('request_kpi_update')
@require_admin_role
def handle_kpi_update_request():
    """Handle KPI data update request"""
    client_id = request.sid
    
    try:
        kpi_data = get_current_kpi_data()
        
        # Update cache
        analytics_cache['kpi_data'] = kpi_data
        analytics_cache['kpi_last_update'] = datetime.now()
        
        # Send to requesting client
        emit('kpi_update', {
            'type': 'kpi_data',
            'data': kpi_data,
            'timestamp': datetime.now().isoformat()
        }, room=client_id)
        
        print(f"KPI data sent to admin {client_id}")
        
    except Exception as e:
        emit('error', {'message': f'Error fetching KPI data: {str(e)}'})

@get_socketio().on('request_analytics')
@require_admin_role
def handle_analytics_request():
    """Handle analytics data request"""
    client_id = request.sid
    period = request.args.get('period', 'day')
    
    try:
        analytics = get_analytics_data(period)
        
        # Update cache
        analytics_cache['analytics'] = analytics
        analytics_cache['analytics_last_update'] = datetime.now()
        
        # Send to requesting client
        emit('analytics_update', {
            'type': 'analytics_data',
            'period': period,
            'data': analytics,
            'timestamp': datetime.now().isoformat()
        }, room=client_id)
        
        print(f"Analytics data sent to admin {client_id}")
        
    except Exception as e:
        emit('error', {'message': f'Error fetching analytics: {str(e)}'})

@get_socketio().on('request_leaderboard')
@require_admin_role
def handle_leaderboard_request():
    """Handle leaderboard data request"""
    client_id = request.sid
    leaderboard_type = request.args.get('type', 'all')  # waiters, chefs, all
    
    try:
        leaderboard_data = get_leaderboard_data(leaderboard_type)
        
        # Send to requesting client
        emit('leaderboard_update', {
            'type': 'leaderboard_data',
            'leaderboard_type': leaderboard_type,
            'data': leaderboard_data,
            'timestamp': datetime.now().isoformat()
        }, room=client_id)
        
        print(f"Leaderboard data sent to admin {client_id}")
        
    except Exception as e:
        emit('error', {'message': f'Error fetching leaderboard: {str(e)}'})

@get_socketio().on('request_stock_alerts')
@require_admin_role
def handle_stock_alerts_request():
    """Handle stock alerts request"""
    client_id = request.sid
    
    try:
        stock_alerts = get_stock_alerts()
        
        # Send to requesting client
        emit('stock_alerts_update', {
            'type': 'stock_alerts',
            'data': stock_alerts,
            'timestamp': datetime.now().isoformat()
        }, room=client_id)
        
        print(f"Stock alerts sent to admin {client_id}")
        
    except Exception as e:
        emit('error', {'message': f'Error fetching stock alerts: {str(e)}'})

@get_socketio().on('export_data')
@require_admin_role
def handle_export_request():
    """Handle data export request"""
    client_id = request.sid
    export_type = request.args.get('type', 'all')
    date_range = request.args.get('date_range', 'today')
    
    try:
        export_data = generate_export_data(export_type, date_range)
        
        # Send to requesting client
        emit('export_ready', {
            'type': 'export_data',
            'export_type': export_type,
            'date_range': date_range,
            'data': export_data,
            'timestamp': datetime.now().isoformat()
        }, room=client_id)
        
        print(f"Export data sent to admin {client_id}")
        
    except Exception as e:
        emit('error', {'message': f'Error generating export: {str(e)}'})

# Data fetching functions
def get_current_kpi_data():
    """Get current KPI data from database"""
    try:
        from src.core.database.connection import get_db
        db = get_db()
        cursor = db.cursor()
        
        # Daily revenue
        cursor.execute("""
            SELECT COALESCE(SUM(total_amount), 0) as daily_revenue
            FROM orders 
            WHERE DATE(created_at) = CURRENT_DATE 
            AND status = 'completed'
        """)
        daily_revenue = cursor.fetchone()[0]
        
        # Average preparation time (from analytics)
        cursor.execute("""
            SELECT AVG(completion_time) as avg_prep_time
            FROM order_analytics 
            WHERE DATE(created_at) = CURRENT_DATE
        """)
        avg_prep_time_result = cursor.fetchone()
        avg_prep_time = avg_prep_time_result[0] if avg_prep_time_result[0] else 0
        
        # Top selling product
        cursor.execute("""
            SELECT oi.product_name, SUM(oi.quantity) as total_quantity
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            WHERE DATE(o.created_at) = CURRENT_DATE 
            AND o.status = 'completed'
            GROUP BY oi.product_name
            ORDER BY total_quantity DESC
            LIMIT 1
        """)
        top_product_result = cursor.fetchone()
        top_product = top_product_result[0] if top_product_result else 'N/A'
        
        # Active tables
        cursor.execute("""
            SELECT COUNT(*) as active_tables
            FROM tables 
            WHERE status = 'occupied'
        """)
        active_tables = cursor.fetchone()[0]
        
        # Total tables for percentage
        cursor.execute("SELECT COUNT(*) as total_tables FROM tables")
        total_tables = cursor.fetchone()[0]
        
        # Calculate changes (comparison with yesterday)
        cursor.execute("""
            SELECT COALESCE(SUM(total_amount), 0) as yesterday_revenue
            FROM orders 
            WHERE DATE(created_at) = CURRENT_DATE - INTERVAL '1 day'
            AND status = 'completed'
        """)
        yesterday_revenue = cursor.fetchone()[0]
        
        revenue_change = ((daily_revenue - yesterday_revenue) / yesterday_revenue * 100) if yesterday_revenue > 0 else 0
        
        cursor.close()
        
        return {
            'daily_revenue': {
                'value': float(daily_revenue),
                'change': float(revenue_change),
                'icon': '💰',
                'title': 'Gündəlik Dövriyyə'
            },
            'avg_prep_time': {
                'value': float(avg_prep_time),
                'change': -5.2,  # Simulated change
                'icon': '⏱️',
                'title': 'Orta Hazırlanma Müddəti',
                'unit': 'dəq'
            },
            'top_product': {
                'value': top_product,
                'change': 12.3,  # Simulated change
                'icon': '🍕',
                'title': 'Ən Çox Satan Məhsul'
            },
            'active_tables': {
                'value': int(active_tables),
                'change': 8.5,  # Simulated change
                'icon': '🪑',
                'title': 'Aktiv Masa Sayı',
                'total': int(total_tables)
            }
        }
        
    except Exception as e:
        print(f"Error fetching KPI data: {e}")
        return get_cached_kpi_data()

def get_cached_kpi_data():
    """Get cached KPI data with stampede protection"""
    import time
    
    cache_key = 'kpi_data'
    lock_key = f"{cache_key}_lock"
    
    # Try cache first
    cached = analytics_cache.get(cache_key)
    if cached:
        return cached
    
    # Try to acquire lock for stampede protection
    if analytics_cache.set_nx(lock_key, '1', ex=10):
        try:
            # Compute expensive analytics
            data = compute_expensive_kpi_data()
            analytics_cache.set(cache_key, data, ex=300)  # 5 minutes
            return data
        finally:
            analytics_cache.delete(lock_key)
    else:
        # Wait for other process to populate cache
        time.sleep(0.1)
        cached = analytics_cache.get(cache_key)
        return cached if cached else get_default_kpi_data()

def compute_expensive_kpi_data():
    """Compute expensive KPI data"""
    try:
        from src.core.database.connection import get_db
        db = get_db()
        cursor = db.cursor()
        
        # Get daily revenue
        cursor.execute("""
            SELECT COALESCE(SUM(total_amount), 0) as revenue
            FROM orders 
            WHERE DATE(created_at) = CURRENT_DATE 
            AND status = 'completed'
        """)
        daily_revenue = cursor.fetchone()[0]
        
        # Get average preparation time
        cursor.execute("""
            SELECT AVG(EXTRACT(EPOCH FROM (completed_at - created_at))/60) as avg_time
            FROM orders 
            WHERE DATE(completed_at) = CURRENT_DATE 
            AND status = 'completed'
            AND completed_at IS NOT NULL
        """)
        avg_prep_time = cursor.fetchone()[0] or 0
        
        # Get top product
        cursor.execute("""
            SELECT oi.product_name, SUM(oi.quantity) as total_sold
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            WHERE DATE(o.created_at) = CURRENT_DATE
            AND o.status = 'completed'
            GROUP BY oi.product_name
            ORDER BY total_sold DESC
            LIMIT 1
        """)
        top_product_result = cursor.fetchone()
        top_product = top_product_result[0] if top_product_result else 'N/A'
        
        # Get active tables
        cursor.execute("""
            SELECT COUNT(*) FROM tables WHERE status = 'occupied'
        """)
        active_tables = cursor.fetchone()[0]
        
        return {
            'daily_revenue': {'value': float(daily_revenue), 'change': 0, 'icon': '💰', 'title': 'Gündəlik Dövriyyə'},
            'avg_prep_time': {'value': round(float(avg_prep_time), 1), 'change': 0, 'icon': '⏱️', 'title': 'Orta Hazırlanma Müddəti'},
            'top_product': {'value': top_product, 'change': 0, 'icon': '🍕', 'title': 'Ən Çox Satan Məhsul'},
            'active_tables': {'value': int(active_tables), 'change': 0, 'icon': '🪑', 'title': 'Aktiv Masa Sayı'}
        }
    except Exception as e:
        try:
            print(f"Error computing KPI data: {str(e)}")
        except UnicodeEncodeError:
            print("Error computing KPI data: Database connection error")
        return get_default_kpi_data()

def get_default_kpi_data():
    """Get default KPI data when cache is empty"""
    return {
        'daily_revenue': {'value': 0, 'change': 0, 'icon': '💰', 'title': 'Gündəlik Dövriyyə'},
        'avg_prep_time': {'value': 0, 'change': 0, 'icon': '⏱️', 'title': 'Orta Hazırlanma Müddəti'},
        'top_product': {'value': 'N/A', 'change': 0, 'icon': '🍕', 'title': 'Ən Çox Satan Məhsul'},
        'active_tables': {'value': 0, 'change': 0, 'icon': '🪑', 'title': 'Aktiv Masa Sayı'}
    }

def get_analytics_data(period='day'):
    """Get analytics data based on period"""
    try:
        from src.core.database.connection import get_db
        db = get_db()
        cursor = db.cursor()
        
        if period == 'day':
            # Hourly sales data
            cursor.execute("""
                SELECT EXTRACT(HOUR FROM created_at) as hour, SUM(total_amount) as revenue
                FROM orders 
                WHERE DATE(created_at) = CURRENT_DATE 
                AND status = 'completed'
                GROUP BY EXTRACT(HOUR FROM created_at)
                ORDER BY hour
            """)
        elif period == 'week':
            # Daily sales data for the week
            cursor.execute("""
                SELECT DATE(created_at) as date, SUM(total_amount) as revenue
                FROM orders 
                WHERE created_at >= DATE(CURRENT_DATE - INTERVAL '7 day')
                AND status = 'completed'
                GROUP BY DATE(created_at)
                ORDER BY date
            """)
        elif period == 'month':
            # Weekly sales data for the month
            cursor.execute("""
                SELECT DATE_TRUNC('week', created_at)::date as week, SUM(total_amount) as revenue
                FROM orders 
                WHERE created_at >= DATE(CURRENT_DATE - INTERVAL '30 day')
                AND status = 'completed'
                GROUP BY DATE_TRUNC('week', created_at)
                ORDER BY week
            """)
        
        sales_data = cursor.fetchall()
        cursor.close()
        
        # Format data for charts
        labels = []
        values = []
        
        for row in sales_data:
            if period == 'day':
                labels.append(f"{int(row[0]):02d}")
            elif period == 'week':
                labels.append(row[0].strftime('%a'))
            elif period == 'month':
                labels.append(f"Week {row[0].day}")
            
            values.append(float(row[1]))
        
        return {
            'labels': labels,
            'values': values,
            'period': period
        }
        
    except Exception as e:
        print(f"Error fetching analytics: {e}")
        return {'labels': [], 'values': [], 'period': period}

def get_leaderboard_data(leaderboard_type='all'):
    """Get leaderboard data"""
    try:
        from src.core.database.connection import get_db
        db = get_db()
        cursor = db.cursor()
        
        result = {}
        
        if leaderboard_type in ['all', 'waiters']:
            # Waiter leaderboard (by sales)
            cursor.execute("""
                SELECT u.full_name, COALESCE(SUM(o.total_amount), 0) as total_sales,
                       COUNT(o.id) as order_count
                FROM users u
                LEFT JOIN orders o ON u.id = o.waiter_id AND o.status = 'completed'
                WHERE u.role = 'waiter'
                GROUP BY u.id, u.full_name
                ORDER BY total_sales DESC
                LIMIT 5
            """)
            
            waiters = []
            for i, (name, sales, orders) in enumerate(cursor.fetchall(), 1):
                waiters.append({
                    'name': name,
                    'sales': float(sales),
                    'orders': int(orders),
                    'rank': i
                })
            
            result['waiters'] = waiters
        
        if leaderboard_type in ['all', 'chefs']:
            # Chef leaderboard (by average preparation time)
            cursor.execute("""
                SELECT u.full_name, AVG(oa.completion_time) as avg_time,
                       COUNT(oa.id) as order_count
                FROM users u
                LEFT JOIN order_analytics oa ON u.id = oa.chef_id
                WHERE u.role = 'chef'
                GROUP BY u.id, u.full_name
                HAVING COUNT(oa.id) > 0
                ORDER BY avg_time ASC
                LIMIT 5
            """)
            
            chefs = []
            for i, (name, avg_time, orders) in enumerate(cursor.fetchall(), 1):
                chefs.append({
                    'name': name,
                    'avg_time': float(avg_time),
                    'orders': int(orders),
                    'rank': i
                })
            
            result['chefs'] = chefs
        
        cursor.close()
        return result
        
    except Exception as e:
        print(f"Error fetching leaderboard: {e}")
        return {'waiters': [], 'chefs': []}

def get_stock_alerts():
    """Get stock alerts for critical items"""
    try:
        from src.core.database.connection import get_db
        db = get_db()
        cursor = db.cursor()
        
        # Get items with low stock
        cursor.execute("""
            SELECT p.name, p.current_stock, p.unit, p.min_stock_level
            FROM products p
            WHERE p.current_stock <= p.min_stock_level
            ORDER BY (p.current_stock::float / p.min_stock_level) ASC
            LIMIT 10
        """)
        
        alerts = []
        for name, quantity, unit, min_level in cursor.fetchall():
            alerts.append({
                'product': name,
                'quantity': quantity,
                'unit': unit,
                'min_level': min_level,
                'icon': get_product_emoji(name)
            })
        
        cursor.close()
        return alerts
        
    except Exception as e:
        print(f"Error fetching stock alerts: {e}")
        return []

def get_product_emoji(product_name):
    """Get emoji for product name"""
    emoji_map = {
        'viski': '🥃',
        'şərab': '🍷',
        'şərab': '🍷',
        'bira': '🍺',
        'pizza': '🍕',
        'burger': '🍔',
        'lahmacun': '🫓',
        'tiramisu': '🍰',
        'qəhvə': '☕'
    }
    
    for key, emoji in emoji_map.items():
        if key in product_name.lower():
            return emoji
    
    return '📦'

def generate_export_data(export_type='all', date_range='today'):
    """Generate export data"""
    try:
        from src.core.database.connection import get_db
        db = get_db()
        cursor = db.cursor()
        
        data = {
            'export_type': export_type,
            'date_range': date_range,
            'generated_at': datetime.now().isoformat()
        }
        
        if export_type in ['all', 'orders']:
            # Export orders data
            cursor.execute("""
                SELECT o.id, o.table_id, o.total_amount, o.status, o.created_at,
                       u.full_name as waiter_name
                FROM orders o
                LEFT JOIN users u ON o.waiter_id = u.id
                WHERE DATE(o.created_at) = CASE 
                    WHEN %s = 'today' THEN CURRENT_DATE
                    WHEN %s = 'week' THEN CURRENT_DATE - INTERVAL '7 day'
                    WHEN %s = 'month' THEN CURRENT_DATE - INTERVAL '30 day'
                    ELSE CURRENT_DATE
                END
                ORDER BY o.created_at DESC
            """, (date_range, date_range, date_range))
            
            orders = []
            for row in cursor.fetchall():
                orders.append({
                    'id': row[0],
                    'table_id': row[1],
                    'total_amount': float(row[2]),
                    'status': row[3],
                    'created_at': row[4].isoformat(),
                    'waiter_name': row[5]
                })
            
            data['orders'] = orders
        
        if export_type in ['all', 'analytics']:
            # Export analytics data
            cursor.execute("""
                SELECT DATE(o.created_at) as date, COUNT(*) as order_count,
                       SUM(o.total_amount) as revenue
                FROM orders o
                WHERE o.status = 'completed'
                AND DATE(o.created_at) = CASE 
                    WHEN %s = 'today' THEN CURRENT_DATE
                    WHEN %s = 'week' THEN CURRENT_DATE - INTERVAL '7 day'
                    WHEN %s = 'month' THEN CURRENT_DATE - INTERVAL '30 day'
                    ELSE CURRENT_DATE
                END
                GROUP BY DATE(o.created_at)
                ORDER BY date
            """, (date_range, date_range, date_range))
            
            analytics = []
            for row in cursor.fetchall():
                analytics.append({
                    'date': row[0].isoformat(),
                    'order_count': row[1],
                    'revenue': float(row[2])
                })
            
            data['analytics'] = analytics
        
        cursor.close()
        return data
        
    except Exception as e:
        print(f"Error generating export: {e}")
        return {'error': str(e)}

# External functions for other modules
def broadcast_kpi_update(kpi_data):
    """Broadcast KPI update to all admin clients"""
    socketio = get_socketio()
    socketio.emit('kpi_update', {
        'type': 'kpi_data',
        'data': kpi_data,
        'timestamp': datetime.now().isoformat()
    }, room=ADMIN_ROOM)

def broadcast_analytics_update(analytics_data, period='day'):
    """Broadcast analytics update to all admin clients"""
    socketio = get_socketio()
    socketio.emit('analytics_update', {
        'type': 'analytics_data',
        'period': period,
        'data': analytics_data,
        'timestamp': datetime.now().isoformat()
    }, room=ADMIN_ROOM)

def broadcast_leaderboard_update(leaderboard_type, data):
    """Broadcast leaderboard update to all admin clients"""
    socketio = get_socketio()
    socketio.emit('leaderboard_update', {
        'type': 'leaderboard_data',
        'leaderboard_type': leaderboard_type,
        'data': data,
        'timestamp': datetime.now().isoformat()
    }, room=ADMIN_ROOM)

def broadcast_stock_alert(alert_data):
    """Broadcast stock alert to all admin clients"""
    socketio = get_socketio()
    socketio.emit('stock_alerts_update', {
        'type': 'stock_alert',
        'data': alert_data,
        'timestamp': datetime.now().isoformat()
    }, room=ADMIN_ROOM)

# Background task to update cache
def update_analytics_cache():
    """Update analytics cache periodically"""
    try:
        # Update KPI cache
        kpi_data = get_current_kpi_data()
        analytics_cache['kpi_data'] = kpi_data
        analytics_cache['kpi_last_update'] = datetime.now()
        
        # Update analytics cache
        for period in ['day', 'week', 'month']:
            analytics = get_analytics_data(period)
            analytics_cache[f'analytics_{period}'] = analytics
        
        analytics_cache['analytics_last_update'] = datetime.now()
        
        print("Analytics cache updated")
        
    except Exception as e:
        print(f"Error updating analytics cache: {e}")

def start_admin_cache_tasks():
    """Start background cache update tasks"""
    import threading
    import time
    
    def cache_update_loop():
        while True:
            try:
                update_analytics_cache()
                time.sleep(300)  # Update every 5 minutes
            except Exception as e:
                print(f"Admin cache task error: {e}")
                time.sleep(300)
    
    cache_thread = threading.Thread(target=cache_update_loop, daemon=True)
    cache_thread.start()
    print("Started admin cache update tasks")

__all__ = [
    'broadcast_kpi_update',
    'broadcast_analytics_update',
    'broadcast_leaderboard_update',
    'broadcast_stock_alert'
]
