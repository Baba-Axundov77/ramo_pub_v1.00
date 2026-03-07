#!/bin/bash
# deploy.sh - Enterprise deployment script

set -e

echo "🚀 Enterprise Restaurant Management System Deployment"
echo "=================================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p logs uploads static nginx/ssl monitoring/grafana/{dashboards,datasources}

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration before running production deployment."
fi

# Build Docker images
echo "🔨 Building Docker images..."
docker-compose build

# Start services
echo "🚀 Starting services..."
docker-compose up -d

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 10

# Run database migrations
echo "🗄️ Running database migrations..."
docker-compose exec web alembic upgrade head

# Create initial data
echo "📊 Creating initial data..."
docker-compose exec web python -c "
from database.connection import init_database
ok, msg = init_database()
if ok:
    print('✅ Database initialized successfully')
else:
    print(f'❌ Database initialization failed: {msg}')
"

# Check service health
echo "🏥 Checking service health..."
sleep 20

services=("web" "db" "redis" "nginx" "prometheus" "grafana")
for service in "${services[@]}"; do
    if docker-compose ps $service | grep -q "Up"; then
        echo "✅ $service is running"
    else
        echo "❌ $service is not running"
    fi
done

# Show service URLs
echo ""
echo "🌐 Service URLs:"
echo "================"
echo "📱 Web Application: http://localhost:5000"
echo "📊 Grafana Dashboard: http://localhost:3000 (admin/admin)"
echo "📈 Prometheus: http://localhost:9090"
echo "🔍 Nginx Proxy: http://localhost:80"
echo ""
echo "📝 Logs:"
echo "docker-compose logs -f web"
echo ""
echo "🛑 Stop services:"
echo "docker-compose down"
echo ""
echo "🔄 Restart services:"
echo "docker-compose restart"

# Run health check
echo ""
echo "🏥 Running health check..."
curl -s http://localhost:5000/enterprise/health | python -m json.tool || echo "❌ Health check failed"

echo ""
echo "✅ Deployment completed successfully!"
echo "🎉 Enterprise Restaurant Management System is now running!"
