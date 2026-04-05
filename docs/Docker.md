# Docker

smplFrm is distributed as a single Docker image that bundles the Django web server, Celery worker, and Celery beat scheduler. Only Redis is required as an external service.

## Quick Start

```yaml
services:
    smpl_frm:
        image: dke39vsh3gghs/smplfrm:latest
        ports:
          - "8321:8321"
        environment:
            - SMPL_FRM_LIBRARY_DIRS=/app/library
            - REDIS_HOST=cache
            - PYTHONUNBUFFERED=1
        volumes:
            - /path/to/your/photos:/app/library
        depends_on:
          - cache

    cache:
        image: redis:7.4.1-alpine
        restart: always
```

```bash
docker compose up -d
```

Browse to `http://localhost:8321`.

## Architecture

The container runs three processes via an entrypoint script:

1. **Celery worker** — processes background tasks (image caching, library scanning)
2. **Celery beat** — schedules periodic tasks
3. **Django server** — serves the web UI and REST API (foreground process)

On startup the entrypoint also runs database migrations and collects static files.

## Volume Mounts

| Mount | Container Path | Description |
|-------|---------------|-------------|
| Photo library | `/app/library` | Your photo directories. Set `SMPL_FRM_LIBRARY_DIRS` to match. |
| Database | `/app/src/smplfrm/db` | SQLite database for persistent config, tasks, and plugin state. Optional — a new DB is created if not mounted. |

### Example with DB persistence

```yaml
services:
    smpl_frm:
        image: dke39vsh3gghs/smplfrm:latest
        ports:
          - "8321:8321"
        environment:
            - SMPL_FRM_LIBRARY_DIRS=/app/library
            - REDIS_HOST=cache
            - PYTHONUNBUFFERED=1
        volumes:
            - /path/to/your/photos:/app/library
            - smplfrm-db:/app/src/smplfrm/db
        depends_on:
          - cache

    cache:
        image: redis:7.4.1-alpine
        restart: always

volumes:
  smplfrm-db:
```

## Environment Variables

See [Environment Variables](Environment-Variables) for the full reference of all application, infrastructure, and plugin environment variables.

## Docker Hub

**Repo:** https://hub.docker.com/r/dke39vsh3gghs/smplfrm

| Tag | Description |
|-----|-------------|
| `vX.X.X` | Official releases. Recommended for production. |
| `latest` | Most recent code on `main`. Useful for development and testing. |
| `<commit-hash>` | Pinned to a specific commit on `main`. |

## Updating

```bash
docker compose pull
docker compose up -d
```

Migrations run automatically on container startup.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Container exits immediately | Check logs: `docker compose logs smpl_frm` |
| Redis connection refused | Ensure `REDIS_HOST` matches the Redis service name and `depends_on` is set. |
| Photos not showing | Verify the volume mount path and `SMPL_FRM_LIBRARY_DIRS` match. Check supported formats with `SMPL_FRM_IMAGE_FORMATS`. |
| Port already in use | Stop any local dev server or change the host port mapping. |

## Building from Source

```bash
docker build -f docker/images/Dockerfile -t smplfrm .
```

The build context is the repository root. The Dockerfile is at `docker/images/Dockerfile`.
