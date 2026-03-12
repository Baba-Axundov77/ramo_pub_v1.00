# 🚀 Ramo Pub Deployment Guide
## Enterprise-grade Restaurant Management System

**Version:** v2.2.0  
**Compliance:** 95% AGENTS.md & OPTIMIZATIONS.md  
**Last Updated:** 2024-03-13

---

## 📋 Table of Contents

- [🎯 Prerequisites](#-prerequisites)
- [🏗️ Architecture Overview](#️-architecture-overview)
- [🚀 Quick Start](#-quick-start)
- [🐳 Docker Deployment](#-docker-deployment)
- [⚙️ Production Configuration](#️-production-configuration)
- [🔧 Environment Setup](#-environment-setup)
- [📊 Monitoring & Alerting](#-monitoring--alerting)
- [🔒 Security Considerations](#-security-considerations)
- [🧪 Testing & Validation](#-testing--validation)
- [🚨 Troubleshooting](#-troubleshooting)

---

## 🎯 Prerequisites

### **System Requirements**
- **CPU:** 2+ cores (4+ recommended)
- **RAM:** 4GB+ (8GB+ recommended)
- **Storage:** 20GB+ SSD
- **OS:** Linux (Ubuntu 20.04+), Windows 10+, macOS 10.15+

### **Software Dependencies**
- **Python 3.10+**
- **PostgreSQL 14+**
- **Redis 6+** (optional, for caching)
- **Docker 20.10+** & Docker Compose 2.0+
- **Nginx** (reverse proxy, recommended)

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Ramo Pub Architecture                │
├─────────────────────────────────────────────────────────────┤
│  🌐 Web Layer (Flask + SocketIO)                │
│  ├── 📱 Responsive Web Interface                   │
│  ├── 🔌 Real-time WebSocket Updates                │
│  └── 🛡️ Authentication & Authorization           │
├─────────────────────────────────────────────────────────────┤
│  🖥️ Desktop Layer (PyQt6)                        │
│  ├── 📊 Native Desktop Experience                  │
│  ├── 🔄 Real-time Synchronization                 │
│  └── 💾 Local Data Caching                       │
├─────────────────────────────────────────────────────────────┤
│  🔧 Business Logic Layer                             │
│  ├── 📦 Modular Services (POS, Inventory, etc.)    │
│  ├── 🔒 Connection Safety (Context Managers)       │
│  └── 📈 Analytics & Reporting                    │
├─────────────────────────────────────────────────────────────┤
│  🗄️ Data Layer                                      │
│  ├── 🐘 PostgreSQL Database                      │
│  ├── ⚡ Redis Cache (Optional)                   │
│  └── 🔄 Migration System (Alembic)               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### **1. Clone Repository**
```bash
git clone https://github.com/Baba-Axundov77/ramo_pub_v1.00.git
cd ramo_pub_v1.00
```

### **2. Environment Setup**
```bash
# Copy environment template
cp .env.example .env

# Edit with your configuration
nano .env
```

### **3. Database Setup**
```bash
# Create PostgreSQL database
createdb ramo_pub

# Run migrations
alembic upgrade head
```

### **4. Start Application**
```bash
# Development mode
python run.py

# Production mode
docker-compose up -d
```

---

## 🐳 Docker Deployment

### **Production Dockerfile**
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser /app
USER appuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Start application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "src.main:app"]
```

### **Docker Compose**
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - DB_HOST=db
      - DB_PORT=5432
      - DB_NAME=ramo_pub
      - DB_USER=postgres
      - DB_PASSWORD=${DB_PASSWORD}
      - REDIS_HOST=redis
      - FLASK_SECRET_KEY=${FLASK_SECRET_KEY}
    depends_on:
      - db
      - redis
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs
      - ./uploads:/app/uploads

  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=ramo_pub
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    restart: unless-stopped
    ports:
      - "5432:5432"

  redis:
    image: redis:6-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped
    ports:
      - "6379:6379"

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - web
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

---

## ⚙️ Production Configuration

### **Environment Variables**
```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ramo_pub
DB_USER=postgres
DB_PASSWORD=your_secure_password

# Flask Configuration
FLASK_SECRET_KEY=your_very_long_secret_key_here
FLASK_ENV=production
FLASK_DEBUG=false

# Redis Configuration (Optional)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password

# WebSocket Configuration
WEBSOCKET_CORS_ALLOWED_ORIGINS=https://yourdomain.com
WEBSOCKET_ASYNC_MODE=gevent

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=/app/logs/ramo_pub.log

# Security Configuration
SESSION_TIMEOUT=3600
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION=900
```

### **Database Optimization**
```sql
-- PostgreSQL performance settings
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = '0.9';
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = '100';
SELECT pg_reload_conf();
```

---

## 🔧 Environment Setup

### **Development Environment**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements/requirements.txt

# Run development server
python run.py
```

### **Production Environment**
```bash
# Using Docker Compose (Recommended)
docker-compose -f docker-compose.prod.yml up -d

# Using systemd service
sudo systemctl start ramo-pub
sudo systemctl enable ramo-pub
```

---

## 📊 Monitoring & Alerting

### **Application Metrics**
- **Connection Pool Utilization** - Monitor database connections
- **WebSocket Client Count** - Track active connections
- **Request Response Times** - Performance monitoring
- **Error Rates** - Application health
- **Memory Usage** - Resource utilization

### **Health Check Endpoints**
```bash
# Application health
curl https://yourdomain.com/api/health

# Database health
curl https://yourdomain.com/api/health/db

# WebSocket health
curl https://yourdomain.com/api/health/websocket
```

### **Monitoring Stack**
```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana

  node-exporter:
    image: prom/node-exporter
    ports:
      - "9100:9100"

volumes:
  grafana_data:
```

---

## 🔒 Security Considerations

### **Network Security**
- **HTTPS Only** - Use SSL/TLS in production
- **Firewall Rules** - Restrict database access
- **VPN Access** - Secure admin access
- **Rate Limiting** - Prevent brute force attacks

### **Application Security**
- **Environment Variables** - Never hardcode secrets
- **Database Encryption** - Enable data-at-rest encryption
- **Session Security** - Secure cookie settings
- **Input Validation** - Sanitize all user inputs

### **Database Security**
```sql
-- Create dedicated user
CREATE USER ramo_pub_app WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE ramo_pub TO ramo_pub_app;
GRANT USAGE ON SCHEMA public TO ramo_pub_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ramo_pub_app;
```

---

## 🧪 Testing & Validation

### **Pre-deployment Checklist**
- [ ] All migrations applied successfully
- [ ] Environment variables configured
- [ ] SSL certificates installed
- [ ] Database backups enabled
- [ ] Monitoring configured
- [ ] Load testing completed
- [ ] Security scan passed

### **Load Testing**
```bash
# Using Apache Bench
ab -n 1000 -c 100 https://yourdomain.com/api/menu

# Using Locust
locust -f load_test.py --host=https://yourdomain.com --users=100 --spawn-rate=10
```

### **Integration Testing**
```bash
# Run compliance tests
python -m pytest tests/test_compliance.py -v

# Run integration tests
python -m pytest tests/integration/ -v
```

---

## 🚨 Troubleshooting

### **Common Issues**

#### **Database Connection Errors**
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Check connection limits
SELECT * FROM pg_stat_activity WHERE state = 'active';

# Monitor connection pool
curl http://localhost:5000/api/health/db
```

#### **WebSocket Connection Issues**
```bash
# Check WebSocket connections
curl -i -N -H "Connection: Upgrade" \
     -H "Upgrade: websocket" \
     -H "Sec-WebSocket-Key: test" \
     -H "Sec-WebSocket-Version: 13" \
     http://localhost:5000/socket.io/

# Check client cleanup
curl http://localhost:5000/api/health/websocket
```

#### **Performance Issues**
```bash
# Check slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

# Check memory usage
free -h
docker stats
```

### **Log Analysis**
```bash
# Application logs
tail -f /app/logs/ramo_pub.log

# Database logs
tail -f /var/log/postgresql/postgresql.log

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

---

## 📞 Support & Contact

- **Documentation:** https://docs.ramo-pub.com
- **Compliance Report:** https://docs.ramo-pub.com/compliance
- **GitHub Issues:** https://github.com/Baba-Axundov77/ramo_pub_v1.00/issues
- **Technical Support:** support@ramo-pub.com
- **Security Issues:** security@ramo-pub.com

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**🎉 Ramo Pub - Enterprise Restaurant Management System**

**Made with ❤️ and dedication to excellence in Azerbaijan** 🇦🇿
