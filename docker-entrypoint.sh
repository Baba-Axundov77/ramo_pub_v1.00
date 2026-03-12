#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# RAMO PUB - DOCKER ENTRYPOINT SCRIPT
# Production startup with health checks and monitoring
# ═══════════════════════════════════════════════════════════════

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to wait for database
wait_for_db() {
    log_info "Waiting for database connection..."
    
    # Extract database connection details from DATABASE_URL
    if [[ $DATABASE_URL =~ postgresql://([^:]+):([^@]+)@([^:]+):([0-9]+)/(.+) ]]; then
        DB_USER="${BASH_REMATCH[1]}"
        DB_PASSWORD="${BASH_REMATCH[2]}"
        DB_HOST="${BASH_REMATCH[3]}"
        DB_PORT="${BASH_REMATCH[4]}"
        DB_NAME="${BASH_REMATCH[5]}"
    else
        log_error "Invalid DATABASE_URL format"
        exit 1
    fi
    
    # Wait for database to be ready
    max_attempts=30
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT 1;" >/dev/null 2>&1; then
            log_info "Database is ready!"
            return 0
        fi
        
        log_warn "Database connection attempt $attempt/$max_attempts failed. Retrying in 2 seconds..."
        sleep 2
        ((attempt++))
    done
    
    log_error "Database connection failed after $max_attempts attempts"
    exit 1
}

# Function to wait for Redis
wait_for_redis() {
    log_info "Waiting for Redis connection..."
    
    # Extract Redis connection details
    if [[ $REDIS_URL =~ redis://([^:]+):([0-9]+)/(.+) ]]; then
        REDIS_HOST="${BASH_REMATCH[1]}"
        REDIS_PORT="${BASH_REMATCH[2]}"
        REDIS_DB="${BASH_REMATCH[3]}"
    else
        REDIS_HOST=${REDIS_HOST:-localhost}
        REDIS_PORT=${REDIS_PORT:-6379}
        REDIS_DB=${REDIS_DB:-0}
    fi
    
    # Wait for Redis to be ready
    max_attempts=30
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if redis-cli -h $REDIS_HOST -p $REDIS_PORT -n $REDIS_DB ping >/dev/null 2>&1; then
            log_info "Redis is ready!"
            return 0
        fi
        
        log_warn "Redis connection attempt $attempt/$max_attempts failed. Retrying in 2 seconds..."
        sleep 2
        ((attempt++))
    done
    
    log_error "Redis connection failed after $max_attempts attempts"
    exit 1
}

# Function to run database migrations
run_migrations() {
    log_info "Running database migrations..."
    
    # Check if we need to run migrations
    if [ "$ENABLE_RUNTIME_AUTO_MIGRATE" = "true" ]; then
        log_info "Runtime auto-migrate is enabled"
        
        # Run Flask migrations
        python -c "
from web.app import create_app, db
from flask_migrate import upgrade
import sys

app = create_app()
with app.app_context():
    try:
        upgrade()
        print('Migrations completed successfully')
    except Exception as e:
        print(f'Migration failed: {e}')
        sys.exit(1)
"
        
        if [ $? -eq 0 ]; then
            log_info "Database migrations completed successfully"
        else
            log_error "Database migrations failed"
            exit 1
        fi
    else
        log_info "Runtime auto-migrate is disabled"
    fi
}

# Function to initialize application
initialize_app() {
    log_info "Initializing Ramo Pub application..."
    
    # Create necessary directories
    mkdir -p logs uploads static/css static/js static/images
    
    # Set proper permissions
    chmod 755 logs uploads static
    chmod 644 logs/*
    
    # Initialize application data
    python -c "
from web.app import create_app, db
from web.models import User, Table, Product
import sys

app = create_app()
with app.app_context():
    try:
        # Create admin user if not exists
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@ramo-pub.com',
                full_name='System Administrator',
                role='admin'
            )
            admin_user.set_password('$RAMO_DEFAULT_ADMIN_PASSWORD')
            db.session.add(admin_user)
            db.session.commit()
            print('Admin user created successfully')
        
        # Create sample tables if not exists
        if Table.query.count() == 0:
            sample_tables = [
                Table(table_number=1, capacity=4, status='available'),
                Table(table_number=2, capacity=4, status='available'),
                Table(table_number=3, capacity=6, status='available'),
                Table(table_number=4, capacity=6, status='available'),
                Table(table_number=5, capacity=8, status='available'),
                Table(table_number=6, capacity=8, status='available'),
                Table(table_number=7, capacity=4, status='available'),
                Table(table_number=8, capacity=4, status='available'),
            ]
            
            for table_data in sample_tables:
                table = Table(**table_data)
                db.session.add(table)
            
            db.session.commit()
            print('Sample tables created successfully')
        
        print('Application initialization completed')
        
    except Exception as e:
        print(f'Application initialization failed: {e}')
        sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        log_info "Application initialization completed successfully"
    else
        log_error "Application initialization failed"
        exit 1
    fi
}

# Function to check application health
health_check() {
    log_info "Performing application health check..."
    
    # Check if the application can start
    python -c "
from web.app import create_app
import sys

try:
    app = create_app()
    with app.test_client() as client:
        response = client.get('/api/health')
        if response.status_code == 200:
            print('Health check passed')
            sys.exit(0)
        else:
            print(f'Health check failed: HTTP {response.status_code}')
            sys.exit(1)
except Exception as e:
    print(f'Health check failed: {e}')
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        log_info "Health check passed"
        return 0
    else
        log_error "Health check failed"
        return 1
    fi
}

# Function to start the application
start_application() {
    log_info "Starting Ramo Pub application..."
    
    # Set default command if not provided
    if [ $# -eq 0 ]; then
        # Default to gunicorn for production
        set -- gunicorn --bind 0.0.0.0:5000 \
                   --workers $GUNICORN_WORKERS \
                   --threads $GUNICORN_THREADS \
                   --timeout $GUNICORN_TIMEOUT \
                   --keepalive $GUNICORN_KEEPALIVE \
                   --max-requests $GUNICORN_MAX_REQUESTS \
                   --max-requests-jitter $GUNICORN_MAX_REQUESTS_JITTER \
                   --access-logfile - \
                   --error-logfile - \
                   --log-level info \
                   --capture-output \
                   --worker-class gevent \
                   web.app:app
    fi
    
    # Start the application
    log_info "Executing: $@"
    exec "$@"
}

# Function to handle graceful shutdown
graceful_shutdown() {
    log_info "Received shutdown signal, performing graceful shutdown..."
    
    # Send SIGTERM to gunicorn master process
    if [ -f /tmp/gunicorn.pid ]; then
        kill -TERM $(cat /tmp/gunicorn.pid)
        log_info "Sent SIGTERM to gunicorn master process"
        
        # Wait for graceful shutdown
        sleep 10
        
        # Force kill if still running
        if [ -f /tmp/gunicorn.pid ]; then
            kill -KILL $(cat /tmp/gunicorn.pid)
            log_info "Force killed gunicorn master process"
        fi
    fi
    
    exit 0
}

# Function to handle signals
setup_signal_handlers() {
    trap graceful_shutdown SIGTERM SIGINT
    trap 'log_info "Received SIGHUP, ignoring..."' SIGHUP
}

# Main execution flow
main() {
    log_info "Starting Ramo Pub Docker container..."
    log_info "Environment: $FLASK_ENV"
    log_info "Python version: $(python --version)"
    
    # Setup signal handlers
    setup_signal_handlers
    
    # Validate required environment variables
    if [ -z "$DATABASE_URL" ]; then
        log_error "DATABASE_URL environment variable is required"
        exit 1
    fi
    
    if [ -z "$SECRET_KEY" ]; then
        log_error "SECRET_KEY environment variable is required"
        exit 1
    fi
    
    # Wait for dependencies
    wait_for_db
    wait_for_redis
    
    # Run migrations if enabled
    run_migrations
    
    # Initialize application
    initialize_app
    
    # Perform health check
    health_check
    
    # Start the application
    start_application "$@"
}

# Execute main function
main "$@"
