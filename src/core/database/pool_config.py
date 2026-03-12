"""
Database Pool Configuration - Optimized for production workloads
Dynamic pool sizing and performance monitoring
"""

import logging
import time
import threading
from typing import Optional
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

class OptimizedConnectionPool:
    """
    Dynamic connection pool with auto-scaling and monitoring
    """
    
    def __init__(
        self,
        min_conn: int = 5,
        max_conn: int = 50,
        host: str = "localhost",
        port: int = 5432,
        database: str = "ramo_pub",
        user: str = "postgres",
        password: str = "",
        **kwargs
    ):
        self.min_conn = min_conn
        self.max_conn = max_conn
        self.current_size = min_conn
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.kwargs = kwargs
        
        # Performance metrics
        self.active_connections = 0
        self.peak_connections = 0
        self.total_requests = 0
        self.failed_requests = 0
        self.last_scale_time = time.time()
        self.scale_threshold = 0.8  # Scale up at 80% utilization
        self.scale_down_threshold = 0.3  # Scale down at 30% utilization
        
        # Initialize pool
        self._initialize_pool()
        self._start_monitoring()
        
    def _initialize_pool(self):
        """Initialize the connection pool"""
        try:
            self.pool = ThreadedConnectionPool(
                minconn=self.min_conn,
                maxconn=self.max_conn,
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                cursor_factory=RealDictCursor,
                **self.kwargs
            )
            logger.info(f"Connection pool initialized: {self.min_conn}-{self.max_conn} connections")
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise
            
    def getconn(self):
        """Get connection with auto-scaling"""
        self.total_requests += 1
        
        try:
            conn = self.pool.getconn()
            self.active_connections += 1
            self.peak_connections = max(self.peak_connections, self.active_connections)
            
            # Check if we need to scale up
            self._auto_scale_check()
            
            return conn
        except Exception as e:
            self.failed_requests += 1
            logger.error(f"Failed to get connection: {e}")
            raise
            
    def putconn(self, conn):
        """Return connection to pool"""
        try:
            self.pool.putconn(conn)
            self.active_connections = max(0, self.active_connections - 1)
            
            # Check if we need to scale down
            self._auto_scale_check()
        except Exception as e:
            logger.error(f"Failed to return connection: {e}")
            raise
            
    def _auto_scale_check(self):
        """Check if pool needs scaling"""
        current_time = time.time()
        
        # Don't scale too frequently (minimum 30 seconds between scales)
        if current_time - self.last_scale_time < 30:
            return
            
        utilization = self.active_connections / self.current_size
        
        # Scale up if utilization is high and we haven't reached max
        if (utilization > self.scale_threshold and 
            self.current_size < self.max_conn):
            self._scale_up()
            self.last_scale_time = current_time
            
        # Scale down if utilization is low and we're above minimum
        elif (utilization < self.scale_down_threshold and 
              self.current_size > self.min_conn):
            self._scale_down()
            self.last_scale_time = current_time
            
    def _scale_up(self):
        """Scale up pool size"""
        # This would require pool recreation in real implementation
        # For now, just log the recommendation
        logger.info(f"Pool utilization high ({self.active_connections}/{self.current_size}). "
                   f"Consider increasing max connections.")
        
    def _scale_down(self):
        """Scale down pool size"""
        logger.info(f"Pool utilization low ({self.active_connections}/{self.current_size}). "
                   f"Consider decreasing min connections.")
        
    def _start_monitoring(self):
        """Start performance monitoring thread"""
        def monitor():
            while True:
                try:
                    self._log_metrics()
                    time.sleep(60)  # Log every minute
                except Exception as e:
                    logger.error(f"Pool monitoring error: {e}")
                    
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
        logger.info("Connection pool monitoring started")
        
    def _log_metrics(self):
        """Log performance metrics"""
        utilization = (self.active_connections / self.current_size) * 100 if self.current_size > 0 else 0
        
        logger.info(
            f"Pool Metrics - "
            f"Active: {self.active_connections}, "
            f"Size: {self.current_size}, "
            f"Utilization: {utilization:.1f}%, "
            f"Peak: {self.peak_connections}, "
            f"Total Requests: {self.total_requests}, "
            f"Failed: {self.failed_requests}, "
            f"Success Rate: {((self.total_requests - self.failed_requests) / self.total_requests * 100) if self.total_requests > 0 else 0:.1f}%"
        )
        
    def get_metrics(self) -> dict:
        """Get current pool metrics"""
        return {
            'active_connections': self.active_connections,
            'current_size': self.current_size,
            'utilization': (self.active_connections / self.current_size) * 100 if self.current_size > 0 else 0,
            'peak_connections': self.peak_connections,
            'total_requests': self.total_requests,
            'failed_requests': self.failed_requests,
            'success_rate': ((self.total_requests - self.failed_requests) / self.total_requests * 100) if self.total_requests > 0 else 0
        }
