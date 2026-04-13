#!/bin/bash

# CRMSarvam Docker Startup Script
# This script helps with initial setup and startup

set -e

echo "=========================================="
echo "   CRMSarvam Docker Startup Script"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}Warning: docker-compose not found. Trying 'docker compose' instead...${NC}"
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check for .env file
if [ ! -f .env ]; then
    print_error ".env file not found!"
    echo "Please create .env from .env.example:"
    echo "  cp .env.example .env"
    echo "Then edit .env with your configuration"
    exit 1
fi

print_info "Configuration file found: .env"

# Stop existing containers
print_info "Stopping existing containers..."
$DOCKER_COMPOSE down

# Remove old volumes if requested
if [ "$1" == "--clean" ]; then
    print_warning "Removing old volumes (this will delete all data)..."
    $DOCKER_COMPOSE down -v
fi

# Clean build cache
print_info "Cleaning build cache..."
docker builder prune -af

# Build images
print_info "Building Docker images..."
$DOCKER_COMPOSE build --no-cache

# Start services
print_info "Starting services..."
$DOCKER_COMPOSE up -d

# Wait for PostgreSQL to be ready
print_info "Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if docker exec crmsarvam-postgres pg_isready -U postgres > /dev/null 2>&1; then
        print_info "PostgreSQL is ready!"
        break
    fi
    echo -n "."
    sleep 1
done
if ! docker exec crmsarvam-postgres pg_isready -U postgres > /dev/null 2>&1; then
    print_error "PostgreSQL failed to start!"
    exit 1
fi

# Wait for Redis to be ready
print_info "Waiting for Redis to be ready..."
for i in {1..30}; do
    if docker exec crmsarvam-redis redis-cli ping > /dev/null 2>&1; then
        print_info "Redis is ready!"
        break
    fi
    echo -n "."
    sleep 1
done
if ! docker exec crmsarvam-redis redis-cli ping > /dev/null 2>&1; then
    print_error "Redis failed to start!"
    exit 1
fi

# Wait for backend to be ready
print_info "Waiting for backend to be ready..."
for i in {1..60}; do
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        print_info "Backend is ready!"
        break
    fi
    echo -n "."
    sleep 1
done
if ! curl -s http://localhost:8001/health > /dev/null 2>&1; then
    print_warning "Backend health check failed, but containers may still be starting..."
    print_info "Check logs with: $DOCKER_COMPOSE logs -f backend"
else
    # Wait for frontend
    print_info "Waiting for frontend to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:3000 > /dev/null 2>&1; then
            print_info "Frontend is ready!"
            break
        fi
        echo -n "."
        sleep 1
    done
fi

echo ""
echo "=========================================="
echo "   Startup Complete!"
echo "=========================================="
echo ""
print_info "Services are running:"
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8001"
echo "  API Docs:  http://localhost:8001/docs"
echo ""
print_info "Useful commands:"
echo "  View logs:       $DOCKER_COMPOSE logs -f"
echo "  View backend:    $DOCKER_COMPOSE logs -f backend"
echo "  View frontend:   $DOCKER_COMPOSE logs -f frontend"
echo "  Stop all:        $DOCKER_COMPOSE down"
echo "  Restart:         $DOCKER_COMPOSE restart"
echo ""
print_info "To create an admin user, run:"
echo "  docker-compose exec backend python scripts/create_admin.py --username admin --password admin123"
echo ""
