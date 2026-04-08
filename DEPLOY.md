# SoulCraft Deployment Guide

## Prerequisites

- Docker & Docker Compose
- Tailscale (for secure access)
- VPS with ports 80/443 available

## Quick Start

### 1. Clone and Configure

```bash
git clone <repo-url>
cd SoulCraft
cp .env.example .env
# Edit .env with your settings
```

### 2. Deploy with Traefik

```bash
# Using the deploy script
./scripts/deploy.sh

# Or manually
docker-compose -f docker-compose.traefik.yml up -d
```

### 3. Access

- **SoulCraft**: https://soulcraft.YOUR_TAILNET.ts.net
- **Traefik Dashboard**: https://traefik.YOUR_TAILNET.ts.net

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_BASE_URL` | Primary inference server | `http://172.17.0.1:8085/v1` |
| `LLM_FALLBACK_URL` | Backup inference server | (optional) |
| `LLM_MODEL` | Model to use | `gemma-4b` |
| `TRAEFIK_DOMAIN` | Your Tailnet domain | (required) |

### Tailscale Setup

1. Install Tailscale on VPS:
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
   ```

2. Enable HTTPS certificates:
   ```bash
   sudo tailscale cert YOUR_TAILNET.ts.net
   ```

3. Note your Tailnet domain (e.g., `tail1234.ts.net`)

## CI/CD Setup

### GitHub Actions

1. Add secrets to your repository:
   - `VPS_HOST` - Your VPS IP or Tailscale IP
   - `VPS_USER` - SSH user for deployment
   - `VPS_SSH_KEY` - Private key for SSH access

2. Push to `main` branch triggers auto-deployment

### Manual Deployment

```bash
# Build and push image
docker build -t ghcr.io/USER/soulcraft:latest .
docker push ghcr.io/USER/soulcraft:latest

# Deploy on VPS
docker-compose pull
docker-compose up -d
```

## Monitoring

### Health Endpoints

- `/api/health` - Service health
- `/api/diagnostics` - Runtime metrics

### Logs

```bash
# View SoulCraft logs
docker-compose logs -f soulcraft

# View Traefik logs
docker-compose logs -f traefik
```

## Security

- **Tailscale-only access**: All endpoints require Tailscale connection
- **Rate limiting**: 10 req/min per IP (configurable in Traefik)
- **No exposed ports**: Only 80/443 exposed, internal services isolated

## Troubleshooting

### Container won't start

```bash
docker-compose logs soulcraft
```

### Inference server unreachable

```bash
# Test from inside container
docker exec -it soulcraft python -c "from soulcraft.llm import is_available; print(is_available())"
```

### Reset data

```bash
docker volume rm soulcraft_soulcraft-data
```
