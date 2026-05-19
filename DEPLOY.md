# Elixis Deployment Guide

## Architecture

```
[Internet] → [Traefik (443)] → [Elixis (3110)]
                                   ↕
                    [llama-local (8085)] ← primary LLM
                    [Optional OpenAI-compatible fallback]  ← configured only when explicitly set
```

- **VPS**: `srv1542844.hstgr.cloud` (Ubuntu 24.04, Docker + Traefik)
- **Domain**: `elixis.kyanitelabs.tech` (Let's Encrypt via Traefik)
- **LLM primary**: `llama-local` on VPS (Qwen3.5-0.8B via llama.cpp)
- **LLM fallback**: disabled by default; set `LLM_FALLBACK_URL` explicitly only for OpenAI-compatible fallback routing

## Quick Deploy

### From local machine

```bash
VPS_HOST=srv1542844.hstgr.cloud ADMIN_API_KEY="$(openssl rand -hex 32)" ./scripts/deploy.sh
```

Builds the image locally, transfers it to the VPS, and restarts the container.

### Manual deploy on VPS

```bash
cd /docker/elixis
ADMIN_API_KEY="<long-random-token>" docker compose up -d --build --remove-orphans
```

## First-Time Setup

```bash
# On VPS, create the project directory
mkdir -p /docker/elixis

# Clone the repo
cd /docker/elixis
git clone <repo-url> .

# Build and start
ADMIN_API_KEY="<long-random-token>" docker compose up -d --build
```

## CI/CD

Push to `main` triggers auto-deployment via GitHub Actions. CI builds and pushes the container image, copies `docker-compose.yml` to the VPS, logs the VPS into GHCR, persists `ELIXIS_IMAGE` in `/docker/elixis/.env` to the pushed SHA image, starts Compose, and fails the deploy if the running `elixis` container does not report that exact image.

Required production environment secrets: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, `ADMIN_API_KEY`.
The deploy job intentionally fails when any of these are missing. A green deploy means the workflow reached the VPS and verified the running container image; it is not allowed to silently skip production deployment.

## Monitoring

```bash
# Health check
curl https://elixis.kyanitelabs.tech/api/health

# View logs
ssh root@srv1542844.hstgr.cloud "docker compose -f /docker/elixis/docker-compose.yml logs -f elixis"

# Diagnostics
curl -H "Authorization: Bearer $ADMIN_API_KEY" https://elixis.kyanitelabs.tech/api/diagnostics
```

## Configuration

All config is in `docker-compose.yml` environment variables:

| Variable | Value | Purpose |
|----------|-------|---------|
| `LLM_BASE_URL` | `http://llama-local:8085/v1` | Docker network → llama-local |
| `LLM_FALLBACK_URL` | empty | Optional OpenAI-compatible fallback endpoint |
| `LLM_MODEL` | `Qwen3.5-0.8B-Q4_K_M.gguf` | Model file in llama.cpp |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` | secret | Cloud inference credentials when `LLM_PROVIDER=anthropic` |
| `ADMIN_API_KEY` | secret | Required for diagnostics, run history, backups, and cache deletion |
| `ELIXIS_DATA_DIR` | `/app/.elixis` | Persistent run, trace, and cache data directory |
| `ELIXIS_BACKUP_DIR` | `/app/.elixis/backups` | Backup archive directory inside the persistent Docker volume |
| `CORS_ORIGIN` | `https://elixis.kyanitelabs.tech` | Allowed origin |
| `VPS_HOST` | deploy target | Required by `scripts/deploy.sh` |

## Data

Persistent data lives in the `elixis-data` Docker volume (`/app/.elixis` inside container).
In-app backups are stored under `/app/.elixis/backups`, so archive files survive container replacement with the rest of the run data.

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
