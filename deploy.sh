#!/bin/bash

# TripC.AI Chatbot API Deployment Script
# Usage: ./deploy.sh [development|production]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default environment
ENVIRONMENT=${1:-development}

echo -e "${BLUE}🚀 TripC.AI Chatbot API Deployment${NC}"
echo -e "${BLUE}Environment: ${YELLOW}$ENVIRONMENT${NC}"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    echo -e "${YELLOW}Please copy env_example.txt to .env and configure your settings${NC}"
    exit 1
fi

# Load environment variables
source .env

# Check required environment variables
echo -e "${BLUE}🔍 Checking environment variables...${NC}"

REQUIRED_VARS=("OPENAI_API_KEY" "TRIPC_API_TOKEN")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo -e "${RED}❌ Missing required environment variables:${NC}"
    for var in "${MISSING_VARS[@]}"; do
        echo -e "${RED}   - $var${NC}"
    done
    exit 1
fi

echo -e "${GREEN}✅ All required environment variables are set${NC}"

# Create necessary directories
echo -e "${BLUE}📁 Creating directories...${NC}"
mkdir -p logs
mkdir -p backups
mkdir -p ssl

# Stop existing containers
echo -e "${BLUE}🛑 Stopping existing containers...${NC}"
if [ "$ENVIRONMENT" = "production" ]; then
    docker-compose -f docker-compose.prod.yml down
else
    docker-compose down
fi

# Remove old images (optional)
read -p "Do you want to remove old images? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}🧹 Removing old images...${NC}"
    docker system prune -f
fi

# Build and start containers
echo -e "${BLUE}🔨 Building and starting containers...${NC}"
if [ "$ENVIRONMENT" = "production" ]; then
    docker-compose -f docker-compose.prod.yml up -d --build
else
    docker-compose up -d --build
fi

# Wait for services to be ready
echo -e "${BLUE}⏳ Waiting for services to be ready...${NC}"
sleep 30

# Check service health
echo -e "${BLUE}🏥 Checking service health...${NC}"

# Check API health
API_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health || echo "000")
if [ "$API_HEALTH" = "200" ]; then
    echo -e "${GREEN}✅ API is healthy${NC}"
else
    echo -e "${RED}❌ API health check failed (HTTP $API_HEALTH)${NC}"
fi

# Check PostgreSQL health
PG_HEALTH=$(docker exec tripc-postgres pg_isready -U tripc_user -d tripc_chatbot 2>/dev/null && echo "OK" || echo "FAIL")
if [ "$PG_HEALTH" = "OK" ]; then
    echo -e "${GREEN}✅ PostgreSQL is healthy${NC}"
else
    echo -e "${RED}❌ PostgreSQL health check failed${NC}"
fi

# Check Redis health
REDIS_HEALTH=$(docker exec tripc-redis redis-cli ping 2>/dev/null | grep -q "PONG" && echo "OK" || echo "FAIL")
if [ "$REDIS_HEALTH" = "OK" ]; then
    echo -e "${GREEN}✅ Redis is healthy${NC}"
else
    echo -e "${RED}❌ Redis health check failed${NC}"
fi

# Show container status
echo -e "${BLUE}📊 Container status:${NC}"
if [ "$ENVIRONMENT" = "production" ]; then
    docker-compose -f docker-compose.prod.yml ps
else
    docker-compose ps
fi

# Show logs
echo -e "${BLUE}📋 Recent logs:${NC}"
if [ "$ENVIRONMENT" = "production" ]; then
    docker-compose -f docker-compose.prod.yml logs --tail=20 tripc-chatbot-api
else
    docker-compose logs --tail=20 tripc-chatbot-api
fi

echo ""
echo -e "${GREEN}🎉 Deployment completed!${NC}"
echo -e "${BLUE}API URL: ${YELLOW}http://localhost:8000${NC}"
echo -e "${BLUE}API Docs: ${YELLOW}http://localhost:8000/docs${NC}"
echo -e "${BLUE}Health Check: ${YELLOW}http://localhost:8000/health${NC}"

if [ "$ENVIRONMENT" = "production" ]; then
    echo -e "${BLUE}HTTPS URL: ${YELLOW}https://localhost${NC}"
fi

echo ""
echo -e "${BLUE}📝 Useful commands:${NC}"
echo -e "${YELLOW}  View logs:${NC} docker-compose logs -f"
echo -e "${YELLOW}  Stop services:${NC} docker-compose down"
echo -e "${YELLOW}  Restart services:${NC} docker-compose restart"
echo -e "${YELLOW}  Update services:${NC} ./deploy.sh $ENVIRONMENT"
