# 🚀 Ramo Pub - Production Deployment Guide

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Environment Setup](#environment-setup)
4. [Docker Deployment](#docker-deployment)
5. [SSL Configuration](#ssl-configuration)
6. [Blue-Green Deployment](#blue-green-deployment)
7. [Monitoring & Logging](#monitoring--logging)
8. [Backup & Recovery](#backup--recovery)
9. [Security Checklist](#security-checklist)
10. [Troubleshooting](#troubleshooting)

## 🎯 Overview

This guide covers the complete production deployment of the Ramo Pub Restaurant Management System using Docker, Nginx, SSL, and blue-green deployment strategy for zero-downtime updates.

### Architecture Components

- **Web Application**: Flask-based Python application with Gunicorn
- **Database**: PostgreSQL 15 with performance optimizations
- **Cache**: Redis 7 for session storage and caching
- **Reverse Proxy**: Nginx with SSL termination and load balancing
- **Monitoring**: Prometheus + Grafana for metrics and visualization
- **Containerization**: Docker with multi-stage builds
- **Deployment**: Blue-Green strategy for zero-downtime

## 🔧 Prerequisites

### System Requirements

- **Operating System**: Ubuntu 20.04+ / CentOS 8+ / RHEL 8+
- **CPU**: Minimum 4 cores (8+ recommended for production)
- **RAM**: Minimum 8GB (16GB+ recommended for production)
- **Storage**: Minimum 50GB SSD (100GB+ recommended)
- **Network**: Stable internet connection with static IP

### Software Requirements

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install additional tools
sudo apt install -y curl wget git htop nginx-certbot python3-certbot-nginx
```

### Domain Requirements

- **Domain Name**: Registered domain (e.g., ramo-pub.com)
- **DNS Configuration**: A record pointing to server IP
- **Email Address**: For SSL certificate registration
- **SSL Certificate**: Let's Encrypt (automated) or custom certificate

## 🌍 Environment Setup

### 1. Clone Repository

```bash
# Clone the repository
git clone https://github.com/your-org/ramo-pub.git
cd ramo-pub

# Create necessary directories
mkdir -p logs uploads nginx/ssl nginx/conf.d monitoring/rules
```

### 2. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit environment file
nano .env
```

**Critical Environment Variables:**

```bash
# Database Configuration
DB_PASSWORD=CHANGE_THIS_SECURE_PASSWORD_32_CHARS_MIN
DATABASE_URL=postgresql+psycopg2://postgres:CHANGE_THIS_SECURE_PASSWORD_32_CHARS_MIN@localhost:5432/ramo_pub

# Application Security
SECRET_KEY=CHANGE_THIS_32_CHAR_SECRET_KEY_IN_PRODUCTION
JWT_SECRET_KEY=CHANGE_THIS_32_CHAR_JWT_SECRET_KEY_IN_PRODUCTION

# SSL Configuration
DOMAIN=ramo-pub.com
EMAIL=admin@ramo-pub.com

# Monitoring
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
GRAFANA_PASSWORD=CHANGE_THIS_GRAFANA_PASSWORD
```

### 3. SSL Certificate Setup

```bash
# Make SSL setup script executable
chmod +x scripts/setup-ssl.sh

# Run SSL setup
./scripts/setup-ssl.sh -d ramo-pub.com -e admin@ramo-pub.com
```

## 🐳 Docker Deployment

### 1. Build and Start Services

```bash
# Build all services
docker-compose build

# Start all services
docker-compose up -d

# Check service status
docker-compose ps
```

### 2. Verify Services

```bash
# Check application health
curl http://localhost:5000/api/health

# Check database connection
docker-compose exec db pg_isready -U postgres

# Check Redis connection
docker-compose exec redis redis-cli ping

# Check Nginx status
docker-compose exec nginx nginx -t
```

### 3. Initialize Database

```bash
# Run database migrations
docker-compose exec web python -c "
from web.app import create_app, db
from flask_migrate import upgrade
app = create_app()
with app.app_context():
    upgrade()
"

# Create admin user
docker-compose exec web python -c "
from web.app import create_app, db
from web.models import User
app = create_app()
with app.app_context():
    admin = User(username='admin', email='admin@ramo-pub.com', full_name='System Administrator', role='admin')
    admin.set_password('your_admin_password')
    db.session.add(admin)
    db.session.commit()
"
```

## 🔒 SSL Configuration

### Automatic Setup with Let's Encrypt

```bash
# Run SSL setup script
./scripts/setup-ssl.sh -d yourdomain.com -e admin@yourdomain.com

# Test SSL configuration
./scripts/setup-ssl.sh --test

# Monitor certificate expiration
./scripts/setup-ssl.sh --monitor
```

### Manual SSL Setup

1. **Generate CSR:**
```bash
openssl req -new -newkey rsa:2048 -nodes -keyout nginx/ssl/privkey.pem -out nginx/ssl/cert.csr
```

2. **Obtain Certificate** (use your preferred CA)

3. **Configure Nginx:**
```bash
# Copy certificates
cp your-cert.pem nginx/ssl/fullchain.pem
cp your-key.pem nginx/ssl/privkey.pem
cp your-chain.pem nginx/ssl/chain.pem

# Test configuration
docker-compose exec nginx nginx -t

# Reload Nginx
docker-compose exec nginx nginx -s reload
```

### Auto-Renewal Setup

```bash
# Add to crontab
crontab -e

# Add these lines:
0 2 * * * /path/to/ramo-pub/scripts/renew-ssl.sh >> /var/log/ssl-renewal.log 2>&1
0 8 * * * /path/to/ramo-pub/scripts/monitor-ssl.sh >> /var/log/ssl-monitor.log 2>&1
```

## 🔄 Blue-Green Deployment

### Deployment Script Usage

```bash
# Make deployment script executable
chmod +x scripts/deploy.sh

# Deploy to green environment (default)
./scripts/deploy.sh

# Deploy to blue environment
./scripts/deploy.sh -e blue -c green

# Deploy with custom settings
./scripts/deploy.sh -e green -c blue --no-rollback

# Test deployment health check
./scripts/deploy.sh --test

# Rollback to previous deployment
./scripts/deploy.sh --rollback

# Create backup only
./scripts/deploy.sh --backup-only
```

### Deployment Process

1. **Backup Current Deployment**
   - Database dump
   - Configuration files
   - Environment variables

2. **Deploy Target Environment**
   - Pull latest images
   - Build target environment
   - Start target containers

3. **Health Check**
   - Verify application health
   - Test database connectivity
   - Check API endpoints

4. **Traffic Switch**
   - Update Nginx configuration
   - Reload Nginx
   - Monitor traffic

5. **Cleanup**
   - Stop old environment
   - Remove unused containers
   - Clean up resources

### Zero-Downtime Strategy

The blue-green deployment ensures zero downtime by:

- **Parallel Environments**: Blue and green environments run simultaneously
- **Health Checks**: Comprehensive health validation before traffic switch
- **Instant Switch**: Nginx reload for instant traffic redirection
- **Automatic Rollback**: Immediate rollback on failure detection
- **Gradual Traffic**: Optional gradual traffic shifting

## 📊 Monitoring & Logging

### Prometheus Metrics

Access Prometheus at: `http://your-server:9090`

**Key Metrics:**
- Application response time
- Database query performance
- Redis cache hit ratio
- Nginx request rate
- System resource usage

### Grafana Dashboard

Access Grafana at: `http://your-server:3000`

**Default Credentials:**
- Username: `admin`
- Password: Set in `.env` file

**Available Dashboards:**
- Application Performance
- Database Metrics
- System Resources
- Business KPIs

### Log Management

**Application Logs:**
```bash
# View application logs
docker-compose logs -f web

# View Nginx logs
docker-compose logs -f nginx

# View database logs
docker-compose logs -f db
```

**Log Files Location:**
- Application: `logs/app.log`
- Nginx: `logs/nginx/`
- Deployment: `/var/log/deploy.log`
- SSL: `/var/log/ssl-setup.log`

### Error Tracking with Sentry

Configure Sentry in `.env`:
```bash
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
SENTRY_ENVIRONMENT=production
SENTRY_RELEASE=1.0.0
```

## 💾 Backup & Recovery

### Automated Backups

```bash
# Enable backup in .env
BACKUP_ENABLED=true
BACKUP_SCHEDULE=0 2 * * *  # Daily at 2 AM
BACKUP_RETENTION_DAYS=30
BACKUP_S3_BUCKET=ramo-pub-backups
BACKUP_ENCRYPTION_KEY=CHANGE_THIS_32_CHAR_BACKUP_KEY
```

### Manual Backup

```bash
# Database backup
docker-compose exec db pg_dump -U postgres ramo_pub > backup_$(date +%Y%m%d_%H%M%S).sql

# Application backup
tar -czf app_backup_$(date +%Y%m%d_%H%M%S).tar.gz uploads/ logs/ .env docker-compose.yml

# Full system backup
docker-compose down
tar -czf full_backup_$(date +%Y%m%d_%H%M%S).tar.gz .
docker-compose up -d
```

### Recovery Procedures

**Database Recovery:**
```bash
# Stop application
docker-compose stop web

# Restore database
docker-compose exec -T db psql -U postgres -d ramo_pub < backup_file.sql

# Start application
docker-compose start web
```

**Full System Recovery:**
```bash
# Extract backup
tar -xzf full_backup_20231201_020000.tar.gz

# Restore environment
cp .env.backup .env

# Start services
docker-compose up -d
```

## 🔒 Security Checklist

### Pre-Deployment Security

- [ ] **Environment Variables**: All secrets changed from defaults
- [ ] **Database Password**: Strong password (32+ characters)
- [ ] **SSL Certificate**: Valid certificate installed
- [ ] **Firewall**: Only necessary ports open (80, 443, 22)
- [ ] **User Permissions**: Non-root user for containers
- [ ] **File Permissions**: Proper file permissions set

### Application Security

- [ ] **JWT Tokens**: Secure secret keys configured
- [ ] **Session Security**: Secure cookies enabled
- [ ] **CORS Configuration**: Proper origins set
- [ ] **Rate Limiting**: API rate limiting enabled
- [ ] **Input Validation**: All inputs validated
- [ ] **SQL Injection**: Parameterized queries used

### Infrastructure Security

- [ ] **Docker Security**: Docker security scan run
- [ ] **Nginx Security**: Security headers configured
- [ ] **SSL Configuration**: Strong SSL/TLS settings
- [ ] **Backup Encryption**: Backup encryption enabled
- [ ] **Monitoring**: Security monitoring setup
- [ ] **Access Control**: Proper access controls in place

### Ongoing Security

- [ ] **Regular Updates**: System and dependencies updated
- [ ] **Security Scanning**: Regular security scans
- [ ] **Log Monitoring**: Security events monitored
- [ ] **Certificate Renewal**: SSL certificates monitored
- [ ] **Backup Testing**: Backup recovery tested
- [ ] **Penetration Testing**: Regular security testing

## 🛠️ Troubleshooting

### Common Issues

#### 1. Container Won't Start

```bash
# Check logs
docker-compose logs service_name

# Check resource usage
docker stats

# Restart service
docker-compose restart service_name
```

#### 2. Database Connection Issues

```bash
# Check database status
docker-compose exec db pg_isready -U postgres

# Check database logs
docker-compose logs db

# Test connection from web container
docker-compose exec web python -c "
import psycopg2
try:
    conn = psycopg2.connect('postgresql://postgres:password@db:5432/ramo_pub')
    print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
"
```

#### 3. SSL Certificate Issues

```bash
# Check certificate validity
openssl x509 -in nginx/ssl/fullchain.pem -text -noout

# Test SSL configuration
nginx -t -c nginx/nginx.conf

# Check certificate expiration
./scripts/setup-ssl.sh --monitor
```

#### 4. Performance Issues

```bash
# Check system resources
htop
df -h
free -h

# Check application metrics
curl http://localhost:5000/api/metrics

# Analyze slow queries
docker-compose exec db psql -U postgres -d ramo_pub -c "
SELECT query, mean_time, calls
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
"
```

#### 5. Deployment Failures

```bash
# Check deployment logs
tail -f /var/log/deploy.log

# Rollback to previous version
./scripts/deploy.sh --rollback

# Check health status
./scripts/deploy.sh --test
```

### Emergency Procedures

#### Application Down

1. **Check Service Status:**
```bash
docker-compose ps
```

2. **Restart Services:**
```bash
docker-compose restart
```

3. **Check Logs:**
```bash
docker-compose logs -f
```

4. **Rollback if Needed:**
```bash
./scripts/deploy.sh --rollback
```

#### Database Issues

1. **Check Database Status:**
```bash
docker-compose exec db pg_isready -U postgres
```

2. **Check Database Logs:**
```bash
docker-compose logs db
```

3. **Restart Database:**
```bash
docker-compose restart db
```

4. **Restore from Backup if Needed:**
```bash
docker-compose exec -T db psql -U postgres -d ramo_pub < backup_file.sql
```

### Support and Maintenance

#### Regular Maintenance Tasks

- **Weekly**: Check system resources and logs
- **Monthly**: Update dependencies and containers
- **Quarterly**: Security audit and penetration testing
- **Annually**: Full system review and optimization

#### Monitoring Alerts

Set up alerts for:
- High CPU usage (>80%)
- High memory usage (>80%)
- Disk space usage (>90%)
- Application errors (>5% error rate)
- SSL certificate expiration (<30 days)
- Database connection issues

#### Performance Optimization

- **Database**: Optimize queries and indexes
- **Application**: Profile and optimize code
- **Infrastructure**: Scale resources as needed
- **Caching**: Optimize cache strategies
- **CDN**: Implement CDN for static assets

---

## 📞 Support

For deployment issues or questions:

1. **Check Logs**: Always check application and system logs first
2. **Review Documentation**: Refer to this guide and code documentation
3. **Community**: Check GitHub issues and discussions
4. **Emergency**: Use rollback procedures if deployment fails

## 🎉 Success!

Your Ramo Pub Restaurant Management System is now deployed in production with:

- ✅ **Zero-Downtime Deployment**: Blue-green deployment strategy
- ✅ **SSL Security**: HTTPS with Let's Encrypt certificates
- ✅ **High Availability**: Load balancing and failover
- ✅ **Monitoring**: Comprehensive metrics and logging
- ✅ **Backup Strategy**: Automated backups and recovery
- ✅ **Security Hardening**: Production-ready security configuration

Enjoy your production-ready restaurant management system! 🍽️✨
