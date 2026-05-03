#!/bin/bash
# Elixis deployment script
# Usage: ./scripts/deploy.sh [environment]

set -e

ENVIRONMENT=${1:-production}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Deploying Elixis to $ENVIRONMENT..."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Create one from .env.example"
    exit 1
fi

# Load environment variables
export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)

# Validate required variables
if [ -z "$TRAEFIK_DOMAIN" ]; then
    echo -e "${RED}Error: TRAEFIK_DOMAIN not set in .env${NC}"
    exit 1
fi

cd "$PROJECT_DIR"

# Pull latest images
echo -e "${YELLOW}Pulling latest images...${NC}"
docker-compose -f docker-compose.traefik.yml pull

# Deploy with zero downtime
echo -e "${YELLOW}Starting deployment...${NC}"
docker-compose -f docker-compose.traefik.yml up -d --remove-orphans

# Wait for health check
echo -e "${YELLOW}Waiting for health check...${NC}"
sleep 5

# Check if services are healthy
if docker-compose -f docker-compose.traefik.yml ps | grep -q "healthy"; then
    echo -e "${GREEN}✓ Deployment successful!${NC}"
    echo -e "${GREEN}✓ Elixis available at: https://elixis.$TRAEFIK_DOMAIN${NC}"
else
    echo -e "${RED}✗ Health check failed${NC}"
    echo "Checking logs..."
    docker-compose -f docker-compose.traefik.yml logs --tail=50 elixis
    exit 1
fi

# Cleanup old images
echo -e "${YELLOW}Cleaning up old images...${NC}"
docker system prune -f

echo -e "${GREEN}✓ Deployment complete!${NC}"
