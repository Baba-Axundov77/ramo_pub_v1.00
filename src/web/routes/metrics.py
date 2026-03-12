"""
Metrics Collection Endpoint - Prometheus-compatible metrics
Provides application performance and health metrics
"""

import time
import psutil
from flask import Blueprint, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Create blueprint
metrics_bp = Blueprint('metrics', __name__)

# Define metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
ACTIVE_CONNECTIONS = Gauge('db_connections_active', 'Active database connections')
FAILED_CONNECTIONS = Counter('db_connections_failed_total', 'Failed database connections')
WEBSOCKET_CONNECTIONS = Gauge('websocket_connections_total', 'Active WebSocket connections')
MEMORY_USAGE = Gauge('memory_usage_bytes', 'Memory usage in bytes')
CPU_USAGE = Gauge('cpu_usage_percent', 'CPU usage percentage')

@metrics_bp.route('/metrics')
def metrics():
    """Prometheus metrics endpoint"""
    # Update system metrics
    MEMORY_USAGE.set(psutil.virtual_memory().used)
    CPU_USAGE.set(psutil.cpu_percent())
    
    # Generate metrics
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

@metrics_bp.route('/health/metrics')
def health_metrics():
    """Health check with metrics"""
    return {
        'timestamp': time.time(),
        'metrics': {
            'requests_total': REQUEST_COUNT._value._value.get(),
            'active_connections': ACTIVE_CONNECTIONS._value.get(),
            'websocket_connections': WEBSOCKET_CONNECTIONS._value.get(),
            'memory_usage': psutil.virtual_memory().percent,
            'cpu_usage': psutil.cpu_percent(),
            'uptime': time.time() - start_time
        }
    }

# Track start time
start_time = time.time()

# Import connection manager for metrics
try:
    from src.core.database.pool_config import OptimizedConnectionPool
    # This would be set up in the main application
    # For now, we'll use placeholder values
    ACTIVE_CONNECTIONS.set_function(lambda: 0)  # Placeholder
except ImportError:
    # Fallback if optimized pool not available
    ACTIVE_CONNECTIONS.set_function(lambda: 0)
