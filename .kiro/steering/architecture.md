---
title: Architecture
inclusion: always
---

# Architecture

## Overview
smplFrm is a Django application that serves a digital photo frame UI. It uses Celery for background tasks, Redis for caching, and SQLite for persistence.

## Directory Structure
```
src/smplfrm/smplfrm/
  models/          # Django models (Config, Image, Task, etc.)
  services/        # Core business logic (ImageService, CacheService, etc.)
  views/           # Django views and DRF viewsets
    api/v1/        # REST API endpoints
    serializers/   # DRF serializers
  plugins/         # Plugin system (self-contained feature modules)
    base.py        # BasePlugin class
    spotify/       # Spotify now-playing plugin
    weather/       # Weather data plugin
  presets/         # Config preset JSON files
  tasks/           # Core Celery tasks (non-plugin)
  templates/       # Django HTML templates
  static/          # JS, CSS, and static assets
  tests/           # Test suite mirroring source structure
    models/
    services/
    plugins/       # Plugin tests (spotify/, weather/)
    views/
    tasks/
```

## Plugin System
Plugins are self-contained modules under `plugins/`. Each plugin:
- Extends `BasePlugin` from `plugins/base.py`
- Declares `name` and `description`
- Optionally provides Celery tasks via `get_tasks()` and beat schedules via `get_beat_schedule()`
- Registers in `PLUGIN_REGISTRY` in `plugins/__init__.py`
- Has its own tests under `tests/plugins/{name}/`

Core code (`celery.py`, `tasks/`) never directly imports plugin internals. The registry handles task autodiscovery and beat schedule merging.

### Adding a new plugin
1. Create `plugins/{name}/` directory with `__init__.py`, `{name}.py`
2. Extend `BasePlugin`, set `name` and `description`
3. Add tasks in `plugins/{name}/tasks.py` if needed
4. Add class to `PLUGIN_REGISTRY` in `plugins/__init__.py`
5. Add tests under `tests/plugins/{name}/`

## Config System
- `Config` model stores user-facing settings (display, images, cache, enabled plugins)
- Preset JSON files in `presets/` define system-managed configurations synced on startup
- `ConfigService` manages CRUD, preset sync, and copy-on-write for system-managed configs
- Environment variables seed the initial config on first creation only

## API Conventions
- REST API under `/api/v1/`
- PUT for all updates (no PATCH)
- Plugin APIs under `/api/v1/plugins/{name}/`
- Pagination: 5 per page for list endpoints
