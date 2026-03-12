# web/routes/api_optimized.py - High-Performance API with Caching & Security
from __future__ import annotations

import json
import time
import hashlib
import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, List, Optional, Any

from flask import Blueprint, request, jsonify, g, current_app
from flask_caching import Cache
from sqlalchemy import text, func, and_, or_
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
import redis
import psycopg2
from psycopg2.extras import RealDictCursor

# Import safe connection manager
from src.core.database.connection_manager import get_db_connection, get_db_cursor, SafeConnectionManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Blueprint
api_optimized = Blueprint('api_optimized', __name__)

# Redis Cache Configuration
cache_config = {
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': 'redis://localhost:6379/0',
    'CACHE_DEFAULT_TIMEOUT': 300,  # 5 minutes default
    'CACHE_KEY_PREFIX': 'ramo_pub:',
    'CACHE_REDIS_DB': 0,
    'CACHE_REDIS_PASSWORD': None,
    'CACHE_REDIS_SSL': False
}

# Initialize cache
cache = Cache(config=cache_config)

# Database connection pool with optimization
def get_db_pool():
    """Get optimized database connection pool"""
    try:
        return psycopg2.pool.ThreadedConnectionPool(
            minconn=5,
            maxconn=20,
            host='localhost',
            database='ramo_pub',
            user='postgres',
            password='password',
            options="-c search_path=public",
            cursor_factory=RealDictCursor
        )
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise

# Initialize connection pool
db_pool = get_db_pool()

# Performance monitoring decorator
def monitor_performance(func):
    """Monitor API performance and log slow queries"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            execution_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Log if execution time exceeds 50ms
            if execution_time > 50:
                logger.warning(f"Slow query detected: {func.__name__} took {execution_time:.2f}ms")
            
            # Add performance headers
            if hasattr(result, 'headers'):
                result.headers['X-Response-Time'] = f"{execution_time:.2f}ms"
                result.headers['X-Cache-Status'] = 'MISS'
            
            return result
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"API Error in {func.__name__}: {e} (took {execution_time:.2f}ms)")
            raise
    
    return wrapper

# Security decorator for sensitive operations
def require_sensitive_operation_permission(func):
    """Require special permission for sensitive operations"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Check user permissions
        user_role = getattr(g, 'user_role', 'user')
        
        if user_role not in ['admin', 'manager']:
            return jsonify({
                'error': 'Insufficient permissions for sensitive operation',
                'status': 'permission_denied'
            }), 403
        
        # Log the sensitive operation
        logger.warning(f"Sensitive operation attempted by {user_role}: {func.__name__}")
        
        return func(*args, **kwargs)
    
    return wrapper

# SQL Injection protection decorator
def protect_sql_injection(func):
    """Protect against SQL injection attacks"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Validate input parameters
        if request.method in ['POST', 'PUT', 'PATCH']:
            data = request.get_json() or {}
            
            # Check for potential SQL injection patterns
            sql_patterns = [
                'DROP TABLE', 'DELETE FROM', 'INSERT INTO', 'UPDATE SET',
                'SELECT *', 'UNION SELECT', 'JOIN', 'WHERE 1=1', '--', '/*', '*/',
                'xp_', 'sp_', 'EXEC(', 'script>'
            ]
            
            for key, value in data.items():
                if isinstance(value, str):
                    for pattern in sql_patterns:
                        if pattern.lower() in value.lower():
                            logger.error(f"SQL injection attempt detected: {key}={value}")
                            return jsonify({
                                'error': 'Invalid input detected',
                                'status': 'security_violation'
                            }), 400
        
        return func(*args, **kwargs)
    
    return wrapper

# Cache key generator
def generate_cache_key(prefix: str, **kwargs) -> str:
    """Generate unique cache key"""
    key_data = f"{prefix}:{request.endpoint}:{request.method}"
    
    # Add query parameters
    if request.args:
        key_data += f":{json.dumps(sorted(request.args.items()))}"
    
    # Add user context for personalized data
    if hasattr(g, 'user_id'):
        key_data += f":user_{g.user_id}"
    
    # Add additional kwargs
    if kwargs:
        key_data += f":{json.dumps(sorted(kwargs.items()))}"
    
    # Generate hash for long keys
    if len(key_data) > 200:
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"{prefix}:{key_hash}"
    
    return key_data

# ═══════════════════════════════════════════════════════════════
# 1. CACHED API ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@api_optimized.route('/api/menu', methods=['GET'])
@monitor_performance
@cache.cached(timeout=600, key_prefix=generate_cache_key('menu'))
def get_menu():
    """Get menu items with pagination and caching"""
    try:
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)  # Max 100 per page
        category = request.args.get('category')
        offset = (page - 1) * per_page
        
        # Build query with pagination
        where_clause = "WHERE p.is_active = TRUE"
        params = []
        
        if category:
            where_clause += " AND p.category = %s"
            params.append(category)
        
        # Get total count for pagination
        count_query = f"""
            SELECT COUNT(*) as total
            FROM products p
            {where_clause}
        """
        
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']
        
        # Get paginated products
        query = f"""
            SELECT 
                p.id, p.name, p.description, p.category, 
                p.price, p.cost, p.current_stock, p.min_stock_level,
                p.unit, p.is_active, p.is_seasonal, p.preparation_time,
                p.image_url, p.created_at, p.updated_at
            FROM products p
            {where_clause}
            ORDER BY p.category, p.name
            LIMIT %s OFFSET %s
        """
        
        cursor.execute(query, params + [per_page, offset])
        products = cursor.fetchall()
        
        # Group by category
        menu = {}
        for product in products:
            cat = product['category']
            if cat not in menu:
                menu[cat] = []
            
            menu[cat].append({
                'id': product['id'],
                'name': product['name'],
                'description': product['description'],
                'price': float(product['price']),
                'cost': float(product['cost']),
                'stock': product['current_stock'],
                'min_stock': product['min_stock_level'],
                'unit': product['unit'],
                'is_seasonal': product['is_seasonal'],
                'prep_time': product['preparation_time'],
                'image_url': product['image_url']
            })
        
        cursor.close()
        db_pool.putconn(conn)
        
        return jsonify({
            'success': True,
            'data': menu,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page,
                'has_next': page * per_page < total,
                'has_prev': page > 1
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching menu: {e}")
        return jsonify({
            'error': 'Failed to fetch menu',
            'success': False
        }), 500

@api_optimized.route('/api/tables', methods=['GET'])
@monitor_performance
@cache.cached(timeout=60, key_prefix=generate_cache_key('tables'))
def get_tables():
    """Get tables status with short-term caching"""
    try:
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        query = """
            SELECT 
                t.id, t.table_number, t.capacity, t.status,
                t.current_order_id, t.waiter_id, t.created_at,
                u.full_name as waiter_name,
                o.total_amount as current_order_total
            FROM tables t
            LEFT JOIN users u ON t.waiter_id = u.id
            LEFT JOIN orders o ON t.current_order_id = o.id
            ORDER BY t.table_number
        """
        
        cursor.execute(query)
        tables = cursor.fetchall()
        
        result = []
        for table in tables:
            result.append({
                'id': table['id'],
                'table_number': table['table_number'],
                'capacity': table['capacity'],
                'status': table['status'],
                'current_order_id': table['current_order_id'],
                'waiter_id': table['waiter_id'],
                'waiter_name': table['waiter_name'],
                'current_order_total': float(table['current_order_total'] or 0),
                'created_at': table['created_at'].isoformat()
            })
        
        cursor.close()
        db_pool.putconn(conn)
        
        return jsonify({
            'success': True,
            'data': result,
            'cached': True
        })
        
    except Exception as e:
        logger.error(f"Error fetching tables: {e}")
        return jsonify({
            'error': 'Failed to fetch tables',
            'success': False
        }), 500

@api_optimized.route('/api/orders', methods=['GET'])
@monitor_performance
def get_orders():
    """Get orders with filtering and pagination"""
    try:
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        # Get query parameters with validation
        status = request.args.get('status', '')
        table_id = request.args.get('table_id', type=int)
        waiter_id = request.args.get('waiter_id', type=int)
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Build WHERE clause with parameterized queries
        where_conditions = []
        params = []
        
        if status:
            where_conditions.append("o.status = %s")
            params.append(status)
        
        if table_id:
            where_conditions.append("o.table_id = %s")
            params.append(table_id)
        
        if waiter_id:
            where_conditions.append("o.waiter_id = %s")
            params.append(waiter_id)
        
        if date_from:
            where_conditions.append("DATE(o.created_at) >= %s")
            params.append(date_from)
        
        if date_to:
            where_conditions.append("DATE(o.created_at) <= %s")
            params.append(date_to)
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # Calculate offset for pagination
        offset = (page - 1) * per_page
        
        # Main query with JOIN optimization
        query = f"""
            SELECT 
                o.id, o.table_id, o.waiter_id, o.total_amount,
                o.status, o.created_at, o.updated_at, o.completed_at,
                o.notes, o.priority, o.customer_count, o.payment_method,
                o.discount_amount, o.tax_amount, o.service_charge,
                t.table_number, t.capacity,
                u.full_name as waiter_name,
                COUNT(oi.id) as item_count
            FROM orders o
            JOIN tables t ON o.table_id = t.id
            JOIN users u ON o.waiter_id = u.id
            LEFT JOIN order_items oi ON o.id = oi.order_id
            {where_clause}
            GROUP BY o.id, t.table_number, t.capacity, u.full_name
            ORDER BY o.created_at DESC
            LIMIT %s OFFSET %s
        """
        
        cursor.execute(query, params + [per_page, offset])
        orders = cursor.fetchall()
        
        # Get total count for pagination
        count_query = f"""
            SELECT COUNT(*) as total
            FROM orders o
            {where_clause}
        """
        
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()['total']
        
        result = []
        for order in orders:
            result.append({
                'id': order['id'],
                'table_id': order['table_id'],
                'table_number': order['table_number'],
                'table_capacity': order['capacity'],
                'waiter_id': order['waiter_id'],
                'waiter_name': order['waiter_name'],
                'total_amount': float(order['total_amount']),
                'status': order['status'],
                'created_at': order['created_at'].isoformat(),
                'updated_at': order['updated_at'].isoformat(),
                'completed_at': order['completed_at'].isoformat() if order['completed_at'] else None,
                'notes': order['notes'],
                'priority': order['priority'],
                'customer_count': order['customer_count'],
                'payment_method': order['payment_method'],
                'discount_amount': float(order['discount_amount']),
                'tax_amount': float(order['tax_amount']),
                'service_charge': float(order['service_charge']),
                'item_count': order['item_count']
            })
        
        cursor.close()
        db_pool.putconn(conn)
        
        return jsonify({
            'success': True,
            'data': result,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching orders: {e}")
        return jsonify({
            'error': 'Failed to fetch orders',
            'success': False
        }), 500

# ═══════════════════════════════════════════════════════════════
# 2. SECURE SENSITIVE OPERATIONS
# ═══════════════════════════════════════════════════════════════

@api_optimized.route('/api/orders/<int:order_id>/discount', methods=['POST'])
@monitor_performance
@require_sensitive_operation_permission
@protect_sql_injection
def apply_discount(order_id):
    """Apply discount to order (sensitive operation)"""
    try:
        data = request.get_json()
        if not data or 'discount_amount' not in data:
            return jsonify({
                'error': 'Discount amount is required',
                'success': False
            }), 400
        
        discount_amount = float(data['discount_amount'])
        reason = data.get('reason', '')
        
        if discount_amount < 0 or discount_amount > 1000:
            return jsonify({
                'error': 'Invalid discount amount',
                'success': False
            }), 400
        
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        # Start transaction for atomic operation
        conn.autocommit = False
        
        try:
            # Get current order data for audit
            cursor.execute("""
                SELECT total_amount, waiter_id, status
                FROM orders
                WHERE id = %s
                FOR UPDATE
            """, (order_id,))
            
            order = cursor.fetchone()
            if not order:
                return jsonify({
                    'error': 'Order not found',
                    'success': False
                }), 404
            
            if order['status'] == 'completed':
                return jsonify({
                    'error': 'Cannot discount completed order',
                    'success': False
                }), 400
            
            # Apply discount with proper locking
            cursor.execute("""
                UPDATE orders
                SET 
                    discount_amount = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (discount_amount, order_id))
            
            # Log the sensitive operation
            cursor.execute("""
                INSERT INTO audit_logs (
                    user_id, action, table_name, record_id,
                    old_values, new_values, ip_address, user_agent
                ) VALUES (
                    %s, 'DISCOUNT_APPLIED', 'orders', %s,
                    %s, %s, %s, %s
                )
            """, (
                getattr(g, 'user_id', None),
                order_id,
                json.dumps({'discount_amount': 0}),
                json.dumps({
                    'discount_amount': discount_amount,
                    'reason': reason
                }),
                request.remote_addr,
                request.headers.get('User-Agent', '')
            ))
            
            conn.commit()
            
            # Clear relevant cache
            cache.delete(f"orders:order_{order_id}")
            
            cursor.close()
            db_pool.putconn(conn)
            
            return jsonify({
                'success': True,
                'message': 'Discount applied successfully',
                'data': {
                    'order_id': order_id,
                    'discount_amount': discount_amount
                }
            })
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.autocommit = True
            
    except Exception as e:
        logger.error(f"Error applying discount: {e}")
        return jsonify({
            'error': 'Failed to apply discount',
            'success': False
        }), 500

@api_optimized.route('/api/orders/<int:order_id>', methods=['DELETE'])
@monitor_performance
@require_sensitive_operation_permission
@protect_sql_injection
def delete_order(order_id):
    """Delete order (sensitive operation)"""
    try:
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        # Start transaction
        conn.autocommit = False
        
        try:
            # Get order data for audit
            cursor.execute("""
                SELECT total_amount, waiter_id, status
                FROM orders
                WHERE id = %s
                FOR UPDATE
            """, (order_id,))
            
            order = cursor.fetchone()
            if not order:
                return jsonify({
                    'error': 'Order not found',
                    'success': False
                }), 404
            
            if order['status'] == 'completed':
                return jsonify({
                    'error': 'Cannot delete completed order',
                    'success': False
                }), 400
            
            # Delete order items first (foreign key constraint)
            cursor.execute("""
                DELETE FROM order_items
                WHERE order_id = %s
            """, (order_id,))
            
            # Delete order
            cursor.execute("""
                DELETE FROM orders
                WHERE id = %s
            """, (order_id,))
            
            # Log the sensitive operation
            cursor.execute("""
                INSERT INTO audit_logs (
                    user_id, action, table_name, record_id,
                    old_values, new_values, ip_address, user_agent
                ) VALUES (
                    %s, 'ORDER_DELETED', 'orders', %s,
                    %s, %s, %s, %s
                )
            """, (
                getattr(g, 'user_id', None),
                order_id,
                json.dumps({
                    'total_amount': float(order['total_amount']),
                    'status': order['status']
                }),
                None,
                request.remote_addr,
                request.headers.get('User-Agent', '')
            ))
            
            conn.commit()
            
            # Clear cache
            cache.delete(f"orders:order_{order_id}")
            
            cursor.close()
            db_pool.putconn(conn)
            
            return jsonify({
                'success': True,
                'message': 'Order deleted successfully'
            })
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.autocommit = True
            
    except Exception as e:
        logger.error(f"Error deleting order: {e}")
        return jsonify({
            'error': 'Failed to delete order',
            'success': False
        }), 500

# ═══════════════════════════════════════════════════════════════
# 3. STOCK MANAGEMENT WITH RACE CONDITION PROTECTION
# ═══════════════════════════════════════════════════════════════

@api_optimized.route('/api/inventory/check-stock', methods=['POST'])
@monitor_performance
@protect_sql_injection
def check_stock_availability():
    """Check stock availability with race condition protection"""
    try:
        data = request.get_json()
        if not data or 'items' not in data:
            return jsonify({
                'error': 'Items list is required',
                'success': False
            }), 400
        
        items = data['items']
        if not isinstance(items, list):
            return jsonify({
                'error': 'Items must be a list',
                'success': False
            }), 400
        
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        unavailable_items = []
        
        for item in items:
            product_id = item.get('product_id')
            quantity_needed = item.get('quantity', 1)
            
            if not product_id or quantity_needed <= 0:
                continue
            
            # Check stock with proper locking (SELECT FOR UPDATE)
            cursor.execute("""
                SELECT p.current_stock, p.min_stock_level, p.name
                FROM products p
                WHERE p.id = %s
                FOR UPDATE
            """, (product_id,))
            
            product = cursor.fetchone()
            
            if not product:
                unavailable_items.append({
                    'product_id': product_id,
                    'reason': 'Product not found'
                })
            elif product['current_stock'] < quantity_needed:
                unavailable_items.append({
                    'product_id': product_id,
                    'product_name': product['name'],
                    'available_stock': product['current_stock'],
                    'requested_quantity': quantity_needed,
                    'reason': 'Insufficient stock'
                })
        
        cursor.close()
        db_pool.putconn(conn)
        
        return jsonify({
            'success': True,
            'available': len(unavailable_items) == 0,
            'unavailable_items': unavailable_items
        })
        
    except Exception as e:
        logger.error(f"Error checking stock: {e}")
        return jsonify({
            'error': 'Failed to check stock availability',
            'success': False
        }), 500

@api_optimized.route('/api/inventory/reserve-stock', methods=['POST'])
@monitor_performance
@protect_sql_injection
def reserve_stock():
    """Reserve stock for order (race condition protected)"""
    try:
        data = request.get_json()
        if not data or 'items' not in data:
            return jsonify({
                'error': 'Items list is required',
                'success': False
            }), 400
        
        items = data['items']
        order_id = data.get('order_id')
        
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        # Start transaction for atomic operation
        conn.autocommit = False
        
        try:
            reserved_items = []
            failed_items = []
            
            for item in items:
                product_id = item.get('product_id')
                quantity_needed = item.get('quantity', 1)
                
                if not product_id or quantity_needed <= 0:
                    continue
                
                # Lock the product row to prevent race conditions
                cursor.execute("""
                    SELECT current_stock, min_stock_level, name
                    FROM products
                    WHERE id = %s
                    FOR UPDATE
                """, (product_id,))
                
                product = cursor.fetchone()
                
                if not product:
                    failed_items.append({
                        'product_id': product_id,
                        'reason': 'Product not found'
                    })
                    continue
                
                if product['current_stock'] < quantity_needed:
                    failed_items.append({
                        'product_id': product_id,
                        'product_name': product['name'],
                        'available_stock': product['current_stock'],
                        'requested_quantity': quantity_needed,
                        'reason': 'Insufficient stock'
                    })
                    continue
                
                # Reserve stock (update with proper locking)
                cursor.execute("""
                    UPDATE products
                    SET current_stock = current_stock - %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (quantity_needed, product_id))
                
                # Create reservation record
                cursor.execute("""
                    INSERT INTO stock_reservations (
                        order_id, product_id, quantity_reserved,
                        created_at, expires_at
                    ) VALUES (
                        %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '30 minutes'
                    )
                """, (order_id, product_id, quantity_needed))
                
                reserved_items.append({
                    'product_id': product_id,
                    'product_name': product['name'],
                    'quantity_reserved': quantity_needed
                })
            
            # Check if all items were successfully reserved
            if failed_items:
                conn.rollback()
                return jsonify({
                    'success': False,
                    'message': 'Failed to reserve some items',
                    'failed_items': failed_items,
                    'reserved_items': reserved_items
                }), 400
            
            conn.commit()
            
            cursor.close()
            db_pool.putconn(conn)
            
            return jsonify({
                'success': True,
                'message': 'Stock reserved successfully',
                'reserved_items': reserved_items
            })
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.autocommit = True
            
    except Exception as e:
        logger.error(f"Error reserving stock: {e}")
        return jsonify({
            'error': 'Failed to reserve stock',
            'success': False
        }), 500

# ═══════════════════════════════════════════════════════════════
# 4. PERFORMANCE MONITORING ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@api_optimized.route('/api/performance/stats', methods=['GET'])
@monitor_performance
@require_sensitive_operation_permission
def get_performance_stats():
    """Get performance statistics for monitoring"""
    try:
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        # Get slow query statistics
        cursor.execute("""
            SELECT query, calls, total_time, mean_time, rows
            FROM pg_stat_statements
            WHERE mean_time > 50
            ORDER BY mean_time DESC
            LIMIT 10
        """)
        
        slow_queries = cursor.fetchall()
        
        # Get index usage statistics
        cursor.execute("""
            SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
            FROM pg_stat_user_indexes
            ORDER BY idx_scan DESC
            LIMIT 10
        """)
        
        index_stats = cursor.fetchall()
        
        # Get cache hit ratio
        cursor.execute("""
            SELECT 
                sum(heap_blks_read) as heap_read,
                sum(heap_blks_hit) as heap_hit,
                sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) as ratio
            FROM pg_statio_user_tables
        """)
        
        cache_stats = cursor.fetchone()
        
        cursor.close()
        db_pool.putconn(conn)
        
        return jsonify({
            'success': True,
            'data': {
                'slow_queries': [dict(q) for q in slow_queries],
                'index_usage': [dict(i) for i in index_stats],
                'cache_hit_ratio': {
                    'heap_read': cache_stats['heap_read'],
                    'heap_hit': cache_stats['heap_hit'],
                    'ratio': float(cache_stats['ratio'] or 0)
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching performance stats: {e}")
        return jsonify({
            'error': 'Failed to fetch performance stats',
            'success': False
        }), 500

@api_optimized.route('/api/cache/clear', methods=['POST'])
@monitor_performance
@require_sensitive_operation_permission
def clear_cache():
    """Clear application cache"""
    try:
        # Clear all cache
        cache.clear()
        
        return jsonify({
            'success': True,
            'message': 'Cache cleared successfully'
        })
        
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return jsonify({
            'error': 'Failed to clear cache',
            'success': False
        }), 500

# ═══════════════════════════════════════════════════════════════
# 5. INCREMENTAL BACKUP ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@api_optimized.route('/api/backup/incremental', methods=['GET'])
@monitor_performance
@require_sensitive_operation_permission
def get_incremental_backup():
    """Get incremental backup data"""
    try:
        last_backup_time = request.args.get('last_backup')
        if not last_backup_time:
            return jsonify({
                'error': 'last_backup parameter is required',
                'success': False
            }), 400
        
        try:
            last_backup_dt = datetime.fromisoformat(last_backup_time.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({
                'error': 'Invalid last_backup format. Use ISO format.',
                'success': False
            }), 400
        
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        # Get incremental backup data
        cursor.execute("""
            SELECT * FROM get_incremental_backup_data(%s)
        """, (last_backup_dt,))
        
        backup_data = cursor.fetchall()
        
        cursor.close()
        db_pool.putconn(conn)
        
        return jsonify({
            'success': True,
            'data': [dict(row) for row in backup_data],
            'last_backup': last_backup_time,
            'generated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error generating incremental backup: {e}")
        return jsonify({
            'error': 'Failed to generate incremental backup',
            'success': False
        }), 500

# ═══════════════════════════════════════════════════════════════
# 6. HEALTH CHECK ENDPOINT
# ═══════════════════════════════════════════════════════════════

@api_optimized.route('/api/health', methods=['GET'])
@monitor_performance
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Check database connection
        conn = db_pool.getconn()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        db_pool.putconn(conn)
        
        # Check Redis connection
        redis_client = cache.cache._client
        redis_client.ping()
        
        return jsonify({
            'success': True,
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'services': {
                'database': 'connected',
                'redis': 'connected'
            }
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# ═══════════════════════════════════════════════════════════════
# 7. UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def refresh_materialized_views():
    """Refresh materialized views for performance"""
    try:
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY daily_sales_summary")
        cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY product_performance")
        
        cursor.close()
        db_pool.putconn(conn)
        
        logger.info("Materialized views refreshed successfully")
        
    except Exception as e:
        logger.error(f"Error refreshing materialized views: {e}")

def cleanup_expired_reservations():
    """Clean up expired stock reservations"""
    try:
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        # Release expired reservations
        cursor.execute("""
            WITH expired_reservations AS (
                SELECT sr.product_id, sr.quantity_reserved
                FROM stock_reservations sr
                WHERE sr.expires_at < CURRENT_TIMESTAMP
            )
            UPDATE products p
            SET current_stock = p.current_stock + er.quantity_reserved
            FROM expired_reservations er
            WHERE p.id = er.product_id
        """)
        
        # Delete expired reservation records
        cursor.execute("""
            DELETE FROM stock_reservations
            WHERE expires_at < CURRENT_TIMESTAMP
        """)
        
        conn.commit()
        cursor.close()
        db_pool.putconn(conn)
        
        logger.info("Expired reservations cleaned up")
        
    except Exception as e:
        logger.error(f"Error cleaning up expired reservations: {e}")

# Background task scheduler (run every 5 minutes)
def start_background_tasks():
    """Start background maintenance tasks"""
    import threading
    import time
    
    def maintenance_loop():
        while True:
            try:
                refresh_materialized_views()
                cleanup_expired_reservations()
                time.sleep(300)  # 5 minutes
            except Exception as e:
                logger.error(f"Background task error: {e}")
                time.sleep(60)  # Retry after 1 minute
    
    maintenance_thread = threading.Thread(target=maintenance_loop, daemon=True)
    maintenance_thread.start()
    logger.info("Background maintenance tasks started")

# Initialize background tasks when module loads
start_background_tasks()

__all__ = [
    'api_optimized',
    'get_menu',
    'get_tables',
    'get_orders',
    'apply_discount',
    'delete_order',
    'check_stock_availability',
    'reserve_stock',
    'get_performance_stats',
    'clear_cache',
    'get_incremental_backup',
    'health_check'
]
