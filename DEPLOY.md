# Elixis Deployment Guide

## Architecture

```
[Internet] → [Traefik (443)] → [Elixis (3110)]
                                   ↕
                    [llama-local (8085)] ← primary LLM
                    [LM Studio (1234)]  ← fallback (via Tailscale)
```

- **VPS**: `srv1542844.hstgr.cloud` (Ubuntu 24.04, Docker + Traefik)
- **Domain**: `elixis.kyanitelabs.tech` (Let's Encrypt via Traefik)
- **LLM primary**: `llama-local` on VPS (Qwen3.5-0.8B via llama.cpp)
- **LLM fallback**: LM Studio via Tailscale (`100.66.225.85:1234`)

## Quick Deploy

### From local machine

```bash
./scripts/deploy.sh
```

Builds the image locally, transfers it to the VPS, and restarts the container.

### Manual deploy on VPS

```bash
cd /docker/elixis
docker compose up -d --build --remove-orphans
```

## First-Time Setup

```bash
# On VPS, create the project directory
mkdir -p /docker/elixis

# Clone the repo
cd /docker/elixis
git clone <repo-url> .

# Build and start
docker compose up -d --build
```

## CI/CD

Push to `main` triggers auto-deployment via GitHub Actions.
Required secrets: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`.

## Monitoring

```bash
# Health check
curl https://elixis.kyanitelabs.tech/api/health

# View logs
ssh root@srv1542844.hstgr.cloud "docker compose -f /docker/elixis/docker-compose.yml logs -f elixis"

# Diagnostics
curl https://elixis.kyanitelabs.tech/api/diagnostics
```

## Configuration

All config is in `docker-compose.yml` environment variables:

| Variable | Value | Purpose |
|----------|-------|---------|
| `LLM_BASE_URL` | `http://172.19.0.1:8085/v1` | Docker bridge → llama-local |
| `LLM_FALLBACK_URL` | `http://100.66.225.85:1234/v1` | Tailscale → LM Studio |
| `LLM_MODEL` | `Qwen3.5-0.8B-Q4_K_M.gguf` | Model file in llama.cpp |
| `CORS_ORIGIN` | `https://elixis.kyanitelabs.tech` | Allowed origin |

## Data

Persistent data lives in the `elixis-data` Docker volume (`/app/.elixis` inside container).

```bash
# Inspect
docker volume inspect elixis_elixis-data

# Backup
docker run --rm -v elixis_elixis-data:/data -v $(pwd):/backup alpine tar czf /backup/elixis-data.tar.gz -C /data .
```

## Troubleshooting

### Container won't start
```bash
docker compose -f /docker/elixis/docker-compose.yml logs elixis
```

### LLM unreachable
```bash
# Test from inside container
docker exec elixis python -c "from elixis.llm import is_available; print(is_available())"
```

### Reset data
```bash
docker volume rm elixis_elixis-data
```
