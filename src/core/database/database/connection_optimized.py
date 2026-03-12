# database/connection_optimized.py - High-Performance Database Connection
from __future__ import annotations

import logging
import time
import threading
from contextlib import contextmanager
from typing import Optional, Dict, Any, Generator
from datetime import datetime, timedelta

import psycopg2
from psycopg2 import pool, sql, extras
from psycopg2.extras import RealDictCursor, DictCursor
import redis
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration optimized for high-load
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'ramo_pub',
    'user': 'postgres',
    'password': 'password',
    'min_connections': 5,
    'max_connections': 20,
    'connection_timeout': 30,
    'idle_timeout': 300,
    'max_lifetime': 3600,
    'retry_attempts': 3,
    'retry_delay': 1.0
}

# Redis configuration for caching
REDIS_CONFIG = {
    'host': 'localhost',
    'port': 6379,
    'db': 0,
    'password': None,
    'ssl': False,
    'socket_timeout': 5,
    'socket_connect_timeout': 5,
    'retry_on_timeout': True,
    'health_check_interval': 30
}

# Connection pools
connection_pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None
sqlalchemy_engine = None
redis_client = None

# Performance metrics
performance_metrics = {
    'total_queries': 0,
    'slow_queries': 0,
    'cache_hits': 0,
    'cache_misses': 0,
    'connection_errors': 0,
    'average_query_time': 0.0,
    'last_reset': datetime.now()
}

# Thread lock for thread-safe operations
pool_lock = threading.Lock()

class DatabaseConnectionError(Exception):
    """Custom exception for database connection errors"""
    pass

class QueryTimeoutError(Exception):
    """Custom exception for query timeout errors"""
    pass

class OptimizedDatabaseManager:
    """High-performance database manager with connection pooling and caching"""
    
    def __init__(self):
        self.connection_pool = None
        self.redis_client = None
        self.sqlalchemy_engine = None
        self.session_factory = None
        self._initialize_connections()
    
    def _initialize_connections(self):
        """Initialize all database connections"""
        try:
            self._initialize_postgres_pool()
            self._initialize_redis()
            self._initialize_sqlalchemy()
            logger.info("All database connections initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database connections: {e}")
            raise DatabaseConnectionError(f"Connection initialization failed: {e}")
    
    def _initialize_postgres_pool(self):
        """Initialize PostgreSQL connection pool with optimization"""
        try:
            with pool_lock:
                self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=DB_CONFIG['min_connections'],
                    maxconn=DB_CONFIG['max_connections'],
                    host=DB_CONFIG['host'],
                    port=DB_CONFIG['port'],
                    database=DB_CONFIG['database'],
                    user=DB_CONFIG['user'],
                    password=DB_CONFIG['password'],
                    cursor_factory=RealDictCursor,
                    options="-c search_path=public -c statement_timeout=30000",  # 30s timeout
                    keepalives=1,
                    keepalives_idle=30,
                    keepalives_interval=10,
                    keepalives_count=5
                )
                
                # Test the connection
                conn = self.connection_pool.getconn()
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                self.connection_pool.putconn(conn)
                
                logger.info(f"PostgreSQL pool initialized: {DB_CONFIG['min_connections']}-{DB_CONFIG['max_connections']} connections")
                
        except Exception as e:
            logger.error(f"PostgreSQL pool initialization failed: {e}")
            raise
    
    def _initialize_redis(self):
        """Initialize Redis connection for caching"""
        try:
            self.redis_client = redis.Redis(
                host=REDIS_CONFIG['host'],
                port=REDIS_CONFIG['port'],
                db=REDIS_CONFIG['db'],
                password=REDIS_CONFIG['password'],
                ssl=REDIS_CONFIG['ssl'],
                socket_timeout=REDIS_CONFIG['socket_timeout'],
                socket_connect_timeout=REDIS_CONFIG['socket_connect_timeout'],
                retry_on_timeout=REDIS_CONFIG['retry_on_timeout'],
                health_check_interval=REDIS_CONFIG['health_check_interval'],
                decode_responses=True
            )
            
            # Test Redis connection
            self.redis_client.ping()
            logger.info("Redis connection initialized successfully")
            
        except Exception as e:
            logger.warning(f"Redis connection failed, caching disabled: {e}")
            self.redis_client = None
    
    def _initialize_sqlalchemy(self):
        """Initialize SQLAlchemy engine with optimized settings"""
        try:
            database_url = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
            
            self.sqlalchemy_engine = create_engine(
                database_url,
                poolclass=QueuePool,
                pool_size=DB_CONFIG['min_connections'],
                max_overflow=DB_CONFIG['max_connections'] - DB_CONFIG['min_connections'],
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False,
                connect_args={
                    "options": "-c statement_timeout=30000",
                    "keepalives": 1,
                    "keepalives_idle": 30,
                    "keepalives_interval": 10,
                    "keepalives_count": 5
                }
            )
            
            self.session_factory = scoped_session(
                sessionmaker(bind=self.sqlalchemy_engine, expire_on_commit=False)
            )
            
            logger.info("SQLAlchemy engine initialized successfully")
            
        except Exception as e:
            logger.error(f"SQLAlchemy initialization failed: {e}")
            raise
    
    @contextmanager
    def get_connection(self, timeout: int = 30) -> Generator[psycopg2.extensions.connection, None, None]:
        """Get database connection with timeout and retry logic"""
        start_time = time.time()
        attempts = 0
        
        while attempts < DB_CONFIG['retry_attempts']:
            try:
                if time.time() - start_time > timeout:
                    raise QueryTimeoutError("Database connection timeout")
                
                conn = self.connection_pool.getconn(timeout=5)
                
                # Test connection validity
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                
                try:
                    yield conn
                finally:
                    self.connection_pool.putconn(conn)
                    return
                
            except psycopg2.OperationalError as e:
                attempts += 1
                performance_metrics['connection_errors'] += 1
                logger.warning(f"Connection attempt {attempts} failed: {e}")
                
                if attempts < DB_CONFIG['retry_attempts']:
                    time.sleep(DB_CONFIG['retry_delay'] * attempts)
                else:
                    raise DatabaseConnectionError(f"Failed to get database connection after {attempts} attempts")
            
            except Exception as e:
                if 'conn' in locals():
                    try:
                        self.connection_pool.putconn(conn)
                    except:
                        pass
                raise e
    
    @contextmanager
    def get_session(self) -> Generator[scoped_session, None, None]:
        """Get SQLAlchemy session"""
        try:
            session = self.session_factory()
            yield session
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def execute_query(self, query: str, params: Optional[tuple] = None, 
                     fetch_one: bool = False, fetch_all: bool = True,
                     use_cache: bool = False, cache_timeout: int = 300) -> Any:
        """Execute query with performance monitoring and caching"""
        start_time = time.time()
        
        try:
            # Check cache first
            if use_cache and self.redis_client:
                cache_key = self._generate_cache_key(query, params)
                cached_result = self.redis_client.get(cache_key)
                
                if cached_result:
                    performance_metrics['cache_hits'] += 1
                    logger.debug(f"Cache hit for query: {query[:50]}...")
                    return json.loads(cached_result)
            
            performance_metrics['cache_misses'] += 1
            
            # Execute query
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                if fetch_one:
                    result = cursor.fetchone()
                elif fetch_all:
                    result = cursor.fetchall()
                else:
                    result = cursor.rowcount
                
                cursor.close()
            
            # Cache result if enabled
            if use_cache and self.redis_client and result:
                cache_key = self._generate_cache_key(query, params)
                self.redis_client.setex(
                    cache_key, 
                    cache_timeout, 
                    json.dumps(result, default=str)
                )
            
            # Update performance metrics
            execution_time = (time.time() - start_time) * 1000  # Convert to ms
            performance_metrics['total_queries'] += 1
            
            if execution_time > 50:  # Slow query threshold
                performance_metrics['slow_queries'] += 1
                logger.warning(f"Slow query detected: {execution_time:.2f}ms - {query[:100]}...")
            
            # Update average query time
            total_time = performance_metrics['average_query_time'] * (performance_metrics['total_queries'] - 1)
            performance_metrics['average_query_time'] = (total_time + execution_time) / performance_metrics['total_queries']
            
            return result
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Query execution failed after {execution_time:.2f}ms: {e}")
            raise
    
    def execute_transaction(self, queries: list, params_list: list = None) -> bool:
        """Execute multiple queries in a transaction"""
        if params_list is None:
            params_list = [None] * len(queries)
        
        if len(queries) != len(params_list):
            raise ValueError("Queries and params lists must have the same length")
        
        start_time = time.time()
        
        try:
            with self.get_connection() as conn:
                conn.autocommit = False
                
                try:
                    cursor = conn.cursor()
                    
                    for query, params in zip(queries, params_list):
                        if params:
                            cursor.execute(query, params)
                        else:
                            cursor.execute(query)
                    
                    conn.commit()
                    cursor.close()
                    
                    execution_time = (time.time() - start_time) * 1000
                    logger.info(f"Transaction completed in {execution_time:.2f}ms with {len(queries)} queries")
                    
                    return True
                    
                except Exception as e:
                    conn.rollback()
                    raise e
                finally:
                    conn.autocommit = True
                    
        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            return False
    
    def _generate_cache_key(self, query: str, params: Optional[tuple]) -> str:
        """Generate cache key for query"""
        import hashlib
        
        key_data = f"{query}:{str(params) if params else ''}"
        return f"query_cache:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        uptime = datetime.now() - performance_metrics['last_reset']
        
        return {
            'total_queries': performance_metrics['total_queries'],
            'slow_queries': performance_metrics['slow_queries'],
            'cache_hits': performance_metrics['cache_hits'],
            'cache_misses': performance_metrics['cache_misses'],
            'cache_hit_ratio': performance_metrics['cache_hits'] / max(1, performance_metrics['cache_hits'] + performance_metrics['cache_misses']),
            'connection_errors': performance_metrics['connection_errors'],
            'average_query_time': performance_metrics['average_query_time'],
            'queries_per_second': performance_metrics['total_queries'] / max(1, uptime.total_seconds()),
            'uptime_seconds': uptime.total_seconds(),
            'pool_connections': {
                'min': DB_CONFIG['min_connections'],
                'max': DB_CONFIG['max_connections'],
                'current': self.connection_pool.pool._used + self.connection_pool.pool._idle if self.connection_pool else 0
            }
        }
    
    def reset_performance_metrics(self):
        """Reset performance metrics"""
        global performance_metrics
        performance_metrics = {
            'total_queries': 0,
            'slow_queries': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'connection_errors': 0,
            'average_query_time': 0.0,
            'last_reset': datetime.now()
        }
        logger.info("Performance metrics reset")
    
    def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        health_status = {
            'database': 'unhealthy',
            'redis': 'unhealthy',
            'sqlalchemy': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'issues': []
        }
        
        # Check PostgreSQL
        try:
            with self.get_connection(timeout=5) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1, version()")
                cursor.close()
            health_status['database'] = 'healthy'
        except Exception as e:
            health_status['issues'].append(f"PostgreSQL: {e}")
        
        # Check Redis
        try:
            if self.redis_client:
                self.redis_client.ping()
                health_status['redis'] = 'healthy'
            else:
                health_status['issues'].append("Redis: Not initialized")
        except Exception as e:
            health_status['issues'].append(f"Redis: {e}")
        
        # Check SQLAlchemy
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            health_status['sqlalchemy'] = 'healthy'
        except Exception as e:
            health_status['issues'].append(f"SQLAlchemy: {e}")
        
        return health_status
    
    def cleanup(self):
        """Clean up connections and resources"""
        try:
            if self.connection_pool:
                self.connection_pool.closeall()
                logger.info("PostgreSQL connection pool closed")
            
            if self.redis_client:
                self.redis_client.close()
                logger.info("Redis connection closed")
            
            if self.sqlalchemy_engine:
                self.sqlalchemy_engine.dispose()
                logger.info("SQLAlchemy engine disposed")
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

# Global database manager instance
db_manager = None

def get_db_manager() -> OptimizedDatabaseManager:
    """Get global database manager instance"""
    global db_manager
    if db_manager is None:
        db_manager = OptimizedDatabaseManager()
    return db_manager

def get_db() -> psycopg2.extensions.connection:
    """Get database connection (legacy compatibility)"""
    return get_db_manager().get_connection().__enter__()

def get_session() -> scoped_session:
    """Get SQLAlchemy session"""
    return get_db_manager().get_session().__enter__()

# ═══════════════════════════════════════════════════════════════
# HIGH-LOAD QUERY FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def get_orders_with_performance(conditions: Dict[str, Any] = None, 
                               page: int = 1, per_page: int = 20) -> Dict[str, Any]:
    """Get orders with optimized queries and performance monitoring"""
    db = get_db_manager()
    
    # Build WHERE clause
    where_conditions = []
    params = []
    
    if conditions:
        if 'status' in conditions:
            where_conditions.append("o.status = %s")
            params.append(conditions['status'])
        
        if 'table_id' in conditions:
            where_conditions.append("o.table_id = %s")
            params.append(conditions['table_id'])
        
        if 'date_from' in conditions:
            where_conditions.append("DATE(o.created_at) >= %s")
            params.append(conditions['date_from'])
        
        if 'date_to' in conditions:
            where_conditions.append("DATE(o.created_at) <= %s")
            params.append(conditions['date_to'])
    
    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    # Optimized query with proper indexing
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
    
    # Execute with caching for recent data
    cache_enabled = page == 1 and len(params) == 0  # Cache first page of all orders
    result = db.execute_query(
        query, 
        params + [per_page, (page - 1) * per_page],
        use_cache=cache_enabled,
        cache_timeout=60
    )
    
    # Get total count
    count_query = f"""
        SELECT COUNT(*) as total
        FROM orders o
        {where_clause}
    """
    
    count_result = db.execute_query(count_query, params, fetch_one=True)
    total_count = count_result['total'] if count_result else 0
    
    return {
        'orders': result,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total_count,
            'pages': (total_count + per_page - 1) // per_page
        }
    }

def get_menu_with_cache() -> Dict[str, Any]:
    """Get menu with aggressive caching"""
    db = get_db_manager()
    
    query = """
        SELECT 
            p.id, p.name, p.description, p.category, 
            p.price, p.cost, p.current_stock, p.min_stock_level,
            p.unit, p.is_active, p.is_seasonal, p.preparation_time,
            p.image_url, p.created_at, p.updated_at
        FROM products p
        WHERE p.is_active = TRUE
        ORDER BY p.category, p.name
    """
    
    # Cache menu for 10 minutes (rarely changes)
    products = db.execute_query(query, use_cache=True, cache_timeout=600)
    
    # Group by category
    menu = {}
    for product in products:
        category = product['category']
        if category not in menu:
            menu[category] = []
        
        menu[category].append({
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
    
    return menu

def check_stock_availability_with_lock(items: list) -> Dict[str, Any]:
    """Check stock availability with row-level locking to prevent race conditions"""
    db = get_db_manager()
    
    unavailable_items = []
    
    try:
        with db.get_connection() as conn:
            conn.autocommit = False
            
            try:
                cursor = conn.cursor()
                
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
                
                conn.commit()
                cursor.close()
                
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.autocommit = True
                
    except Exception as e:
        logger.error(f"Error checking stock availability: {e}")
        raise
    
    return {
        'available': len(unavailable_items) == 0,
        'unavailable_items': unavailable_items
    }

# ═══════════════════════════════════════════════════════════════
# BACKGROUND TASKS
# ═══════════════════════════════════════════════════════════════

def start_maintenance_tasks():
    """Start background maintenance tasks"""
    import threading
    import time
    
    def maintenance_loop():
        db = get_db_manager()
        
        while True:
            try:
                # Refresh materialized views
                db.execute_query("REFRESH MATERIALIZED VIEW CONCURRENTLY daily_sales_summary")
                db.execute_query("REFRESH MATERIALIZED VIEW CONCURRENTLY product_performance")
                
                # Clean up expired cache entries
                if db.redis_client:
                    # Clean up old query cache entries
                    keys = db.redis_client.keys("query_cache:*")
                    if keys:
                        db.redis_client.delete(*keys[:100])  # Delete in batches
                
                logger.info("Maintenance tasks completed")
                time.sleep(300)  # Run every 5 minutes
                
            except Exception as e:
                logger.error(f"Maintenance task error: {e}")
                time.sleep(60)  # Retry after 1 minute
    
    maintenance_thread = threading.Thread(target=maintenance_loop, daemon=True)
    maintenance_thread.start()
    logger.info("Background maintenance tasks started")

# Initialize maintenance tasks
start_maintenance_tasks()

# ═══════════════════════════════════════════════════════════════
# CLEANUP ON EXIT
# ═══════════════════════════════════════════════════════════════

import atexit

def cleanup_on_exit():
    """Clean up resources on application exit"""
    global db_manager
    if db_manager:
        db_manager.cleanup()

atexit.register(cleanup_on_exit)

__all__ = [
    'OptimizedDatabaseManager',
    'get_db_manager',
    'get_db',
    'get_session',
    'get_orders_with_performance',
    'get_menu_with_cache',
    'check_stock_availability_with_lock'
]
