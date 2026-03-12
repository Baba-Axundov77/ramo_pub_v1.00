#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# RAMO PUB - SSL SETUP SCRIPT (Let's Encrypt)
# Automated SSL certificate generation and renewal
# ═══════════════════════════════════════════════════════════════

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOMAIN=${DOMAIN:-ramo-pub.com}
EMAIL=${EMAIL:-admin@ramo-pub.com}
STAGING=${STAGING:-false}
CERTBOT_DIR="/etc/letsencrypt"
NGINX_SSL_DIR="./nginx/ssl"
LOG_FILE="/var/log/ssl-setup.log"

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
    log_info "Validating SSL setup prerequisites..."
    
    # Check required commands
    local required_commands=("docker" "docker-compose" "curl")
    for cmd in "${required_commands[@]}"; do
        if ! command_exists $cmd; then
            log_error "Required command '$cmd' is not installed"
            exit 1
        fi
    done
    
    # Check domain is provided
    if [ -z "$DOMAIN" ]; then
        log_error "Domain name is required (export DOMAIN=yourdomain.com)"
        exit 1
    fi
    
    # Check email is provided
    if [ -z "$EMAIL" ]; then
        log_error "Email address is required (export EMAIL=admin@yourdomain.com)"
        exit 1
    fi
    
    # Check if domain resolves to this server
    log_info "Checking if domain $DOMAIN resolves to this server..."
    local server_ip=$(curl -s ifconfig.me)
    local domain_ip=$(dig +short $DOMAIN | head -n 1)
    
    if [ "$server_ip" != "$domain_ip" ]; then
        log_warn "Domain $DOMAIN resolves to $domain_ip, but server IP is $server_ip"
        log_warn "Make sure DNS is properly configured before proceeding"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    log_info "Prerequisites validation completed"
}

# Function to create necessary directories
create_directories() {
    log_info "Creating necessary directories..."
    
    # Create SSL directory
    mkdir -p "$NGINX_SSL_DIR"
    
    # Create certbot directories
    mkdir -p "$CERTBOT_DIR/live/$DOMAIN"
    mkdir -p "$CERTBOT_DIR/archive/$DOMAIN"
    mkdir -p "$CERTBOT_DIR/renewal"
    
    # Create logs directory
    mkdir -p "$(dirname "$LOG_FILE")"
    
    log_info "Directories created"
}

# Function to generate self-signed certificate for initial setup
generate_self_signed_cert() {
    log_info "Generating self-signed certificate for initial setup..."
    
    local openssl_config="/tmp/openssl.conf"
    
    # Create OpenSSL configuration
    cat > "$openssl_config" << EOF
[req]
default_bits = 2048
default_md = sha256
distinguished_name = dn
req_extensions = v3_req
prompt = no

[dn]
CN = $DOMAIN
O = Ramo Pub
OU = IT Department
L = Baku
C = AZ
emailAddress = $EMAIL

[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = $DOMAIN
DNS.2 = www.$DOMAIN
DNS.3 = localhost
IP.1 = 127.0.0.1
EOF
    
    # Generate private key
    openssl genrsa -out "$NGINX_SSL_DIR/privkey.pem" 2048
    
    # Generate certificate
    openssl req -new -x509 -key "$NGINX_SSL_DIR/privkey.pem" \
        -out "$NGINX_SSL_DIR/fullchain.pem" \
        -days 365 \
        -config "$openssl_config"
    
    # Generate chain file (same as fullchain for self-signed)
    cp "$NGINX_SSL_DIR/fullchain.pem" "$NGINX_SSL_DIR/chain.pem"
    
    # Set proper permissions
    chmod 600 "$NGINX_SSL_DIR"/*.pem
    
    # Cleanup
    rm -f "$openssl_config"
    
    log_info "Self-signed certificate generated"
}

# Function to setup Docker containers for Let's Encrypt
setup_certbot_containers() {
    log_info "Setting up Certbot containers..."
    
    # Create docker-compose override for certbot
    cat > docker-compose.certbot.yml << EOF
version: '3.8'

services:
  certbot:
    image: certbot/certbot:latest
    container_name: ramo_pub_certbot
    volumes:
      - ./nginx/ssl:/etc/letsencrypt/live/$DOMAIN
      - $CERTBOT_DIR:/etc/letsencrypt
      - ./nginx/conf.d:/var/www/certbot
    command: >
      certonly
      --webroot
      --webroot-path=/var/www/certbot
      --email $EMAIL
      --agree-tos
      --no-eff-email
      --force-renewal
      -d $DOMAIN
      -d www.$DOMAIN
    depends_on:
      - nginx
    
  nginx:
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./nginx/ssl:/var/www/certbot:ro
EOF
    
    log_info "Certbot containers configured"
}

# Function to obtain Let's Encrypt certificate
obtain_letsencrypt_cert() {
    log_info "Obtaining Let's Encrypt certificate for $DOMAIN..."
    
    # Start Nginx with self-signed certificate
    log_info "Starting Nginx with self-signed certificate..."
    docker-compose up -d nginx
    
    # Wait for Nginx to be ready
    log_info "Waiting for Nginx to be ready..."
    sleep 10
    
    # Run Certbot
    local certbot_args="--webroot --webroot-path=/var/www/certbot --email $EMAIL --agree-tos --no-eff-email --force-renewal -d $DOMAIN -d www.$DOMAIN"
    
    if [ "$STAGING" = "true" ]; then
        certbot_args="$certbot_args --staging"
        log_info "Using Let's Encrypt staging environment"
    fi
    
    # Run certbot container
    docker run --rm \
        --name certbot \
        -v "$CERTBOT_DIR:/etc/letsencrypt" \
        -v "./nginx/conf.d:/var/www/certbot" \
        certbot/certbot:latest \
        certonly $certbot_args
    
    # Check if certificate was obtained
    if [ -f "$CERTBOT_DIR/live/$DOMAIN/fullchain.pem" ]; then
        log_info "Let's Encrypt certificate obtained successfully"
        
        # Copy certificates to nginx directory
        cp "$CERTBOT_DIR/live/$DOMAIN/fullchain.pem" "$NGINX_SSL_DIR/"
        cp "$CERTBOT_DIR/live/$DOMAIN/privkey.pem" "$NGINX_SSL_DIR/"
        cp "$CERTBOT_DIR/live/$DOMAIN/chain.pem" "$NGINX_SSL_DIR/"
        
        # Set proper permissions
        chmod 600 "$NGINX_SSL_DIR"/*.pem
        
        log_info "Certificates copied to Nginx directory"
    else
        log_error "Failed to obtain Let's Encrypt certificate"
        return 1
    fi
}

# Function to test SSL configuration
test_ssl_config() {
    log_info "Testing SSL configuration..."
    
    # Test Nginx configuration
    if docker-compose exec -T nginx nginx -t >/dev/null 2>&1; then
        log_info "Nginx SSL configuration is valid"
    else
        log_error "Nginx SSL configuration is invalid"
        return 1
    fi
    
    # Restart Nginx to apply SSL
    log_info "Restarting Nginx to apply SSL configuration..."
    docker-compose restart nginx
    
    # Wait for Nginx to be ready
    sleep 5
    
    # Test HTTPS connection
    if curl -s -f "https://$DOMAIN" >/dev/null 2>&1; then
        log_info "HTTPS connection test passed"
    else
        log_warn "HTTPS connection test failed (might be expected for self-signed cert)"
    fi
    
    # Test certificate details
    log_info "Certificate details:"
    openssl s_client -connect $DOMAIN:443 -servername $DOMAIN </dev/null 2>/dev/null | openssl x509 -noout -dates -subject || true
    
    log_info "SSL configuration test completed"
}

# Function to setup automatic renewal
setup_auto_renewal() {
    log_info "Setting up automatic certificate renewal..."
    
    # Create renewal script
    cat > scripts/renew-ssl.sh << 'EOF'
#!/bin/bash
# SSL Certificate Renewal Script

set -e

DOMAIN=${DOMAIN:-ramo-pub.com}
CERTBOT_DIR="/etc/letsencrypt"
NGINX_SSL_DIR="./nginx/ssl"

echo "[$(date +'%Y-%m-%d %H:%M:%S')] Starting SSL certificate renewal..."

# Run certbot renewal
docker run --rm \
    --name certbot-renewal \
    -v "$CERTBOT_DIR:/etc/letsencrypt" \
    -v "./nginx/conf.d:/var/www/certbot" \
    certbot/certbot:latest \
    renew --quiet

# Check if certificate was renewed
if [ "$CERTBOT_DIR/live/$DOMAIN/fullchain.pem" -nt "$NGINX_SSL_DIR/fullchain.pem" ]; then
    echo "Certificate renewed, updating Nginx..."
    
    # Copy new certificates
    cp "$CERTBOT_DIR/live/$DOMAIN/fullchain.pem" "$NGINX_SSL_DIR/"
    cp "$CERTBOT_DIR/live/$DOMAIN/privkey.pem" "$NGINX_SSL_DIR/"
    cp "$CERTBOT_DIR/live/$DOMAIN/chain.pem" "$NGINX_SSL_DIR/"
    
    # Restart Nginx
    docker-compose restart nginx
    
    echo "Certificate renewed and Nginx restarted successfully"
else
    echo "Certificate renewal not needed"
fi

echo "SSL certificate renewal completed"
EOF
    
    chmod +x scripts/renew-ssl.sh
    
    # Create cron job for renewal
    local cron_job="0 2 * * * $(pwd)/scripts/renew-ssl.sh >> /var/log/ssl-renewal.log 2>&1"
    
    # Add to crontab
    (crontab -l 2>/dev/null; echo "$cron_job") | crontab -
    
    log_info "Automatic renewal setup completed"
    log_info "Cron job added: $cron_job"
}

# Function to create SSL monitoring
setup_ssl_monitoring() {
    log_info "Setting up SSL monitoring..."
    
    # Create SSL monitoring script
    cat > scripts/monitor-ssl.sh << 'EOF'
#!/bin/bash
# SSL Certificate Monitoring Script

DOMAIN=${DOMAIN:-ramo-pub.com}
ALERT_EMAIL=${ALERT_EMAIL:-admin@ramo-pub.com}

# Check certificate expiration
cert_info=$(openssl s_client -connect $DOMAIN:443 -servername $DOMAIN 2>/dev/null | openssl x509 -noout -dates)
expiry_date=$(echo "$cert_info" | grep "notAfter" | cut -d= -f2)
expiry_timestamp=$(date -d "$expiry_date" +%s)
current_timestamp=$(date +%s)
days_until_expiry=$(( (expiry_timestamp - current_timestamp) / 86400 ))

echo "Certificate for $DOMAIN expires in $days_until_expiry days"

# Alert if certificate expires within 30 days
if [ $days_until_expiry -lt 30 ]; then
    echo "WARNING: Certificate expires in $days_until_expiry days"
    
    # Send email alert
    if command_exists mail; then
        echo "SSL certificate for $DOMAIN expires in $days_until_expiry days" | \
        mail -s "SSL Certificate Expiration Warning" "$ALERT_EMAIL"
    fi
    
    # Send Slack alert (if configured)
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        curl -X POST -H 'Content-type: application/json' \
             --data "{\"text\":\"SSL certificate for $DOMAIN expires in $days_until_expiry days\"}" \
             "$SLACK_WEBHOOK_URL"
    fi
fi
EOF
    
    chmod +x scripts/monitor-ssl.sh
    
    # Add to crontab for daily monitoring
    local monitor_cron="0 8 * * * $(pwd)/scripts/monitor-ssl.sh >> /var/log/ssl-monitor.log 2>&1"
    (crontab -l 2>/dev/null; echo "$monitor_cron") | crontab -
    
    log_info "SSL monitoring setup completed"
}

# Function to display SSL information
display_ssl_info() {
    log_info "SSL Certificate Information:"
    echo "================================"
    echo "Domain: $DOMAIN"
    echo "Email: $EMAIL"
    echo "Staging: $STAGING"
    echo "Certificate files:"
    echo "  - Private key: $NGINX_SSL_DIR/privkey.pem"
    echo "  - Full chain: $NGINX_SSL_DIR/fullchain.pem"
    echo "  - Chain: $NGINX_SSL_DIR/chain.pem"
    echo ""
    echo "Certificate details:"
    openssl x_client -connect $DOMAIN:443 -servername $DOMAIN </dev/null 2>/dev/null | openssl x509 -noout -dates -subject || true
    echo "================================"
}

# Function to cleanup
cleanup() {
    log_info "Cleaning up temporary files..."
    
    # Remove temporary docker-compose file
    rm -f docker-compose.certbot.yml
    
    log_info "Cleanup completed"
}

# Main function
main() {
    log_info "Starting SSL setup for $DOMAIN..."
    
    # Validate prerequisites
    validate_prerequisites
    
    # Create directories
    create_directories
    
    # Generate self-signed certificate for initial setup
    generate_self_signed_cert
    
    # Setup certbot containers
    setup_certbot_containers
    
    # Obtain Let's Encrypt certificate
    if obtain_letsencrypt_cert; then
        log_info "Let's Encrypt certificate obtained successfully"
    else
        log_warn "Let's Encrypt certificate failed, using self-signed certificate"
    fi
    
    # Test SSL configuration
    test_ssl_config
    
    # Setup automatic renewal
    setup_auto_renewal
    
    # Setup SSL monitoring
    setup_ssl_monitoring
    
    # Display SSL information
    display_ssl_info
    
    # Cleanup
    cleanup
    
    log_info "SSL setup completed successfully!"
}

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -d, --domain DOMAIN    Domain name (default: ramo-pub.com)"
    echo "  -e, --email EMAIL      Email address (default: admin@ramo-pub.com)"
    echo "  -s, --staging          Use Let's Encrypt staging environment"
    echo "  -t, --test             Test SSL configuration only"
    echo "  -r, --renew             Renew certificates only"
    echo "  -m, --monitor          Check certificate expiration only"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Setup SSL for ramo-pub.com"
    echo "  $0 -d mydomain.com -e admin@mydomain.com  # Setup SSL for custom domain"
    echo "  $0 -s                                  # Use staging environment"
    echo "  $0 --test                             # Test SSL configuration"
    echo "  $0 --renew                            # Renew certificates"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -d|--domain)
            DOMAIN="$2"
            shift 2
            ;;
        -e|--email)
            EMAIL="$2"
            shift 2
            ;;
        -s|--staging)
            STAGING=true
            shift
            ;;
        -t|--test)
            test_ssl_config
            exit 0
            ;;
        -r|--renew)
            scripts/renew-ssl.sh
            exit 0
            ;;
        -m|--monitor)
            scripts/monitor-ssl.sh
            exit 0
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
