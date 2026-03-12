"""
Database Connection Manager - Safe connection handling with context managers
Ensures proper connection cleanup and prevents leaks in hot paths
"""

import logging
from contextlib import contextmanager
from typing import Generator, Optional
import psycopg2
from psycopg2.pool import ThreadedConnectionPool

logger = logging.getLogger(__name__)

@contextmanager
def get_db_connection(pool: ThreadedConnectionPool) -> Generator:
    """
    Safe database connection context manager
    
    Usage:
        with get_db_connection(db_pool) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM orders")
                result = cur.fetchall()
    """
    conn = None
    try:
        conn = pool.getconn()
        yield conn
    except Exception as e:
        logger.error(f"Failed to get database connection: {e}")
        raise
    finally:
        if conn:
            try:
                pool.putconn(conn)
                logger.debug("Database connection returned to pool")
            except Exception as e:
                logger.error(f"Failed to return connection to pool: {e}")

@contextmanager  
def get_db_cursor(pool: ThreadedConnectionPool) -> Generator:
    """
    Safe database cursor context manager
    
    Usage:
        with get_db_cursor(db_pool) as cur:
            cur.execute("SELECT * FROM orders")
            result = cur.fetchall()
    """
    conn = None
    cur = None
    try:
        conn = pool.getconn()
        cur = conn.cursor()
        yield cur
    except Exception as e:
        logger.error(f"Failed to get database cursor: {e}")
        raise
    finally:
        if cur:
            try:
                cur.close()
                logger.debug("Database cursor closed")
            except Exception as e:
                logger.error(f"Failed to close cursor: {e}")
        if conn:
            try:
                pool.putconn(conn)
                logger.debug("Database connection returned to pool")
            except Exception as e:
                logger.error(f"Failed to return connection to pool: {e}")

class SafeConnectionManager:
    """
    High-level connection manager for database operations
    """
    
    def __init__(self, pool: ThreadedConnectionPool):
        self.pool = pool
        
    def execute_query(self, query: str, params: tuple = None) -> list:
        """Execute query safely with connection management"""
        with get_db_connection(self.pool) as conn:
            with conn.cursor() as cur:
                cur.execute(query, params or ())
                return cur.fetchall()
                
    def execute_update(self, query: str, params: tuple = None) -> int:
        """Execute update safely with connection management"""
        with get_db_connection(self.pool) as conn:
            with conn.cursor() as cur:
                cur.execute(query, params or ())
                return cur.rowcount
                
    def execute_batch(self, query: str, params_list: list) -> int:
        """Execute batch operations safely"""
        with get_db_connection(self.pool) as conn:
            with conn.cursor() as cur:
                cur.executemany(query, params_list)
                return cur.rowcount
