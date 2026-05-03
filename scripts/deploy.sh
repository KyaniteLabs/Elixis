#!/bin/bash
# Elixis deployment script
# Deploys to /docker/elixis on the VPS via SSH

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

VPS_HOST="${VPS_HOST:-187.124.238.235}"
VPS_USER="${VPS_USER:-root}"
REMOTE_DIR="/docker/elixis"

echo "Deploying Elixis to ${VPS_USER}@${VPS_HOST}:${REMOTE_DIR}..."

# Build image locally
echo -e "${YELLOW}Building image...${NC}"
docker build -t elixis:latest --target production "${PROJECT_DIR}"

# Save and transfer image
echo -e "${YELLOW}Transferring image to VPS...${NC}"
docker save elixis:latest | gzip | ssh "${VPS_USER}@${VPS_HOST}" "gunzip | docker load"

# Transfer compose file
echo -e "${YELLOW}Uploading compose file...${NC}"
scp "${PROJECT_DIR}/docker-compose.yml" "${VPS_USER}@${VPS_HOST}:${REMOTE_DIR}/docker-compose.yml"

# Deploy on VPS
echo -e "${YELLOW}Starting deployment...${NC}"
ssh "${VPS_USER}@${VPS_HOST}" << EOF
  cd ${REMOTE_DIR}
  docker compose up -d --remove-orphans
EOF

# Wait for health check
echo -e "${YELLOW}Waiting for health check...${NC}"
sleep 5

# Verify
if ssh "${VPS_USER}@${VPS_HOST}" "docker compose -f ${REMOTE_DIR}/docker-compose.yml ps | grep -q healthy" 2>/dev/null; then
    echo -e "${GREEN}Deployment successful!${GREEN}"
    echo -e "${GREEN}Elixis available at: https://elixis.kyanitelabs.tech${NC}"
else
    echo -e "${RED}Health check failed — checking logs...${NC}"
    ssh "${VPS_USER}@${VPS_HOST}" "docker compose -f ${REMOTE_DIR}/docker-compose.yml logs --tail=50 elixis"
    exit 1
fi

# Cleanup
echo -e "${YELLOW}Cleaning up old images...${NC}"
ssh "${VPS_USER}@${VPS_HOST}" "docker system prune -f"

echo -e "${GREEN}Deployment complete!${NC}"
