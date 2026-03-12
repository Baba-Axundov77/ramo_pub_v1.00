#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# RAMO PUB - BLUE-GREEN DEPLOYMENT SCRIPT
# Zero-downtime deployment with automatic rollback
# ═══════════════════════════════════════════════════════════════

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="ramo-pub"
BACKUP_DIR="/opt/backups"
LOG_FILE="/var/log/deploy.log"
HEALTH_CHECK_URL="http://localhost/api/health"
HEALTH_CHECK_TIMEOUT=30
ROLLBACK_ON_FAILURE=true

# Environment variables
CURRENT_ENVIRONMENT=${CURRENT_ENVIRONMENT:-blue}
TARGET_ENVIRONMENT=${TARGET_ENVIRONMENT:-green}
DEPLOYMENT_TIMEOUT=300

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a $LOG_FILE
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" | tee -a $LOG_FILE
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a $LOG_FILE
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a $LOG_FILE
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to validate prerequisites
validate_prerequisites() {
    log_info "Validating deployment prerequisites..."
    
    # Check required commands
    local required_commands=("docker" "docker-compose" "curl" "jq")
    for cmd in "${required_commands[@]}"; do
        if ! command_exists $cmd; then
            log_error "Required command '$cmd' is not installed"
            exit 1
        fi
    done
    
    # Check Docker daemon
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    # Check environment file
    if [ ! -f ".env" ]; then
        log_error "Environment file '.env' not found"
        exit 1
    fi
    
    # Check docker-compose file
    if [ ! -f "docker-compose.yml" ]; then
        log_error "Docker Compose file not found"
        exit 1
    fi
    
    log_info "Prerequisites validation completed"
}

# Function to backup current deployment
backup_deployment() {
    log_info "Creating backup of current deployment..."
    
    local backup_timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_path="$BACKUP_DIR/$PROJECT_NAME-$backup_timestamp"
    
    # Create backup directory
    mkdir -p "$backup_path"
    
    # Backup database
    log_info "Backing up database..."
    docker-compose exec -T db pg_dump -U postgres ramo_pub > "$backup_path/database.sql"
    
    # Backup environment file
    cp .env "$backup_path/env.backup"
    
    # Backup Docker Compose configuration
    cp docker-compose.yml "$backup_path/docker-compose.yml"
    
    # Store backup path for rollback
    echo "$backup_path" > /tmp/last_backup_path
    
    log_info "Backup completed: $backup_path"
}

# Function to build and deploy target environment
deploy_target_environment() {
    log_info "Deploying to $TARGET_ENVIRONMENT environment..."
    
    # Set target environment profile
    export COMPOSE_PROFILES="$TARGET_ENVIRONMENT"
    
    # Pull latest images
    log_info "Pulling latest Docker images..."
    docker-compose pull
    
    # Build target environment
    log_info "Building $TARGET_ENVIRONMENT environment..."
    docker-compose build web-$TARGET_ENVIRONMENT
    
    # Start target environment
    log_info "Starting $TARGET_ENVIRONMENT environment..."
    docker-compose up -d web-$TARGET_ENVIRONMENT
    
    # Wait for target environment to be ready
    log_info "Waiting for $TARGET_ENVIRONMENT environment to be ready..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker-compose ps web-$TARGET_ENVIRONMENT | grep -q "Up (healthy)"; then
            log_info "$TARGET_ENVIRONMENT environment is healthy and ready"
            return 0
        fi
        
        log_warn "Attempt $attempt/$max_attempts: $TARGET_ENVIRONMENT environment not ready yet"
        sleep 10
        ((attempt++))
    done
    
    log_error "$TARGET_ENVIRONMENT environment failed to become healthy"
    return 1
}

# Function to perform health check on target environment
health_check_target() {
    log_info "Performing health check on $TARGET_ENVIRONMENT environment..."
    
    local target_port=5001
    if [ "$TARGET_ENVIRONMENT" = "blue" ]; then
        target_port=5000
    fi
    
    local health_url="http://localhost:$target_port/api/health"
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$health_url" >/dev/null 2>&1; then
            log_info "Health check passed for $TARGET_ENVIRONMENT environment"
            return 0
        fi
        
        log_warn "Health check attempt $attempt/$max_attempts failed"
        sleep 2
        ((attempt++))
    done
    
    log_error "Health check failed for $TARGET_ENVIRONMENT environment"
    return 1
}

# Function to switch traffic to target environment
switch_traffic() {
    log_info "Switching traffic from $CURRENT_ENVIRONMENT to $TARGET_ENVIRONMENT..."
    
    # Update Nginx configuration to point to target environment
    local nginx_config="nginx/conf.d/ramo-pub.conf"
    local temp_config="$nginx_config.tmp"
    
    # Create backup of current Nginx config
    cp "$nginx_config" "$nginx_config.backup.$(date +%s)"
    
    # Update upstream configuration
    if [ "$TARGET_ENVIRONMENT" = "green" ]; then
        sed 's/server web:5000 max_fails=3 fail_timeout=30s;/server web-green:5001 max_fails=3 fail_timeout=30s;\n    server web:5000 max_fails=3 fail_timeout=30s backup;/' "$nginx_config" > "$temp_config"
    else
        sed 's/server web-green:5001 max_fails=3 fail_timeout=30s backup;/server web:5000 max_fails=3 fail_timeout=30s;\n    server web-green:5001 max_fails=3 fail_timeout=30s backup;/' "$nginx_config" > "$temp_config"
    fi
    
    # Validate Nginx configuration
    if docker-compose exec -T nginx nginx -t >/dev/null 2>&1; then
        mv "$temp_config" "$nginx_config"
        
        # Reload Nginx
        docker-compose exec -T nginx nginx -s reload
        
        # Update current environment variable
        sed -i "s/CURRENT_ENVIRONMENT=.*/CURRENT_ENVIRONMENT=$TARGET_ENVIRONMENT/" .env
        export CURRENT_ENVIRONMENT=$TARGET_ENVIRONMENT
        
        log_info "Traffic successfully switched to $TARGET_ENVIRONMENT environment"
        return 0
    else
        log_error "Invalid Nginx configuration, reverting changes"
        rm -f "$temp_config"
        return 1
    fi
}

# Function to stop old environment
stop_old_environment() {
    local old_environment="green"
    if [ "$TARGET_ENVIRONMENT" = "green" ]; then
        old_environment="blue"
    fi
    
    log_info "Stopping old $old_environment environment..."
    
    # Stop old environment
    docker-compose stop web-$old_environment
    
    log_info "Old $old_environment environment stopped"
}

# Function to rollback deployment
rollback_deployment() {
    log_error "Initiating deployment rollback..."
    
    local backup_path=$(cat /tmp/last_backup_path 2>/dev/null)
    
    if [ -z "$backup_path" ] || [ ! -d "$backup_path" ]; then
        log_error "No backup found for rollback"
        exit 1
    fi
    
    log_info "Rolling back using backup: $backup_path"
    
    # Restore database
    if [ -f "$backup_path/database.sql" ]; then
        log_info "Restoring database from backup..."
        docker-compose exec -T db psql -U postgres -d ramo_pub < "$backup_path/database.sql"
    fi
    
    # Switch traffic back to old environment
    local temp_target=$TARGET_ENVIRONMENT
    TARGET_ENVIRONMENT=$CURRENT_ENVIRONMENT
    switch_traffic
    
    # Start old environment
    export COMPOSE_PROFILES="$TARGET_ENVIRONMENT"
    docker-compose up -d web-$TARGET_ENVIRONMENT
    
    TARGET_ENVIRONMENT=$temp_target
    
    log_error "Rollback completed successfully"
    exit 1
}

# Function to cleanup old containers and images
cleanup_deployment() {
    log_info "Cleaning up old deployment artifacts..."
    
    # Remove unused containers
    docker container prune -f
    
    # Remove unused images
    docker image prune -f
    
    # Remove unused volumes (be careful with this)
    # docker volume prune -f
    
    log_info "Cleanup completed"
}

# Function to monitor deployment
monitor_deployment() {
    log_info "Monitoring deployment for 5 minutes..."
    
    local monitoring_duration=300  # 5 minutes
    local check_interval=30
    local elapsed=0
    
    while [ $elapsed -lt $monitoring_duration ]; do
        if ! health_check_target; then
            log_error "Health check failed during monitoring at $(date)"
            if [ "$ROLLBACK_ON_FAILURE" = "true" ]; then
                rollback_deployment
            fi
            return 1
        fi
        
        log_info "Deployment monitoring: $elapsed/$monitoring_duration seconds passed"
        sleep $check_interval
        elapsed=$((elapsed + check_interval))
    done
    
    log_info "Deployment monitoring completed successfully"
}

# Function to send deployment notification
send_notification() {
    local status=$1
    local message=$2
    
    # Send to Slack (if configured)
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        curl -X POST -H 'Content-type: application/json' \
             --data "{\"text\":\"Ramo Pub Deployment $status: $message\"}" \
             "$SLACK_WEBHOOK_URL" 2>/dev/null || true
    fi
    
    # Send email (if configured)
    if [ -n "$DEPLOYMENT_EMAIL" ] && command_exists mail; then
        echo "$message" | mail -s "Ramo Pub Deployment $status" "$DEPLOYMENT_EMAIL" 2>/dev/null || true
    fi
    
    log_info "Deployment notification sent: $status"
}

# Main deployment function
main() {
    log_info "Starting Ramo Pub Blue-Green Deployment..."
    log_info "Current environment: $CURRENT_ENVIRONMENT"
    log_info "Target environment: $TARGET_ENVIRONMENT"
    
    # Validate prerequisites
    validate_prerequisites
    
    # Backup current deployment
    backup_deployment
    
    # Deploy target environment
    if ! deploy_target_environment; then
        send_notification "FAILED" "Target environment deployment failed"
        if [ "$ROLLBACK_ON_FAILURE" = "true" ]; then
            rollback_deployment
        fi
        exit 1
    fi
    
    # Health check target environment
    if ! health_check_target; then
        send_notification "FAILED" "Target environment health check failed"
        if [ "$ROLLBACK_ON_FAILURE" = "true" ]; then
            rollback_deployment
        fi
        exit 1
    fi
    
    # Switch traffic to target environment
    if ! switch_traffic; then
        send_notification "FAILED" "Traffic switch failed"
        if [ "$ROLLBACK_ON_FAILURE" = "true" ]; then
            rollback_deployment
        fi
        exit 1
    fi
    
    # Monitor deployment
    monitor_deployment
    
    # Stop old environment
    stop_old_environment
    
    # Cleanup
    cleanup_deployment
    
    # Send success notification
    send_notification "SUCCESS" "Deployment completed successfully. Traffic switched to $TARGET_ENVIRONMENT environment"
    
    log_info "Blue-Green deployment completed successfully!"
    log_info "New active environment: $TARGET_ENVIRONMENT"
}

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -e, --environment ENV  Target environment (blue|green) [default: green]"
    echo "  -c, --current ENV      Current environment (blue|green) [default: blue]"
    echo "  -r, --rollback         Rollback to previous deployment"
    echo "  -b, --backup-only      Create backup only"
    echo "  -t, --test             Run health check only"
    echo "  --no-rollback          Disable automatic rollback on failure"
    echo "  --no-cleanup           Skip cleanup after deployment"
    echo ""
    echo "Examples:"
    echo "  $0                    # Deploy to green environment"
    echo "  $0 -e blue -c green   # Deploy to blue environment"
    echo "  $0 --rollback         # Rollback to previous deployment"
    echo "  $0 --test             # Run health check only"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -e|--environment)
            TARGET_ENVIRONMENT="$2"
            shift 2
            ;;
        -c|--current)
            CURRENT_ENVIRONMENT="$2"
            shift 2
            ;;
        -r|--rollback)
            rollback_deployment
            exit 0
            ;;
        -b|--backup-only)
            validate_prerequisites
            backup_deployment
            exit 0
            ;;
        -t|--test)
            health_check_target
            exit 0
            ;;
        --no-rollback)
            ROLLBACK_ON_FAILURE=false
            shift
            ;;
        --no-cleanup)
            SKIP_CLEANUP=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Execute main function
main
