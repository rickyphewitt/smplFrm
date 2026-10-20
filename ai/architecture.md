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
  themes/          # Theme registry (named stylesheets, selected per config)
    base.py        # Theme class
    classic.py     # Classic theme declaration
  presets/         # Config preset JSON files
  tasks/           # Core Celery tasks (non-plugin)
  templates/       # Django HTML templates
  static/          # JS, CSS, and static assets
    css/           # base.css (structural, theme-neutral) plus one file per theme
    icons/         # Vendored icon font subset with license file
    fonts/         # Vendored theme font faces (woff2) with OFL licenses
  tests/           # Test suite mirroring source structure
    models/
    services/
    plugins/       # Plugin tests (spotify/, weather/)
    themes/        # Theme registry tests
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

## Theme System
- A theme is a named stylesheet selected per config; themes have no database row and no migration
- `smplfrm/themes/__init__.py` holds the registry: `THEME_REGISTRY`, `DEFAULT_THEME_ID`, `get_all_themes()`, `get_theme_map()`, `resolve(theme_id)`, mirroring the shape of `PLUGIN_REGISTRY`
- `resolve(theme_id)` is the single resolution point: it returns the default theme and logs a warning for any unknown, empty, or null id, which is what lets a theme be deleted later without a data migration or a broken page
- `Config.theme` is a plain `CharField`, validated in `ConfigSerializer` against the registry rather than via model-level `choices`, so adding a theme never requires a migration
- `GET /api/v1/themes` is a read-only, code-generated JSON:API collection (`id`, `label`, `description`); the `stylesheet` path is never serialized to a client. The frame itself never requests this endpoint — the active theme is resolved server-side in `IndexView` and arrives with the rendered page
- The template loads two stylesheets in order: `static/css/base.css` (structural, theme-neutral) and the active theme's stylesheet (colors, type, radii, shadows)
- The Display tab's Theme control (`#setting-theme`) is populated from the themes endpoint on modal open, in parallel with the config load; the stored value is applied only once options exist, regardless of which request settles first
- `main.js` never branches on the active theme. Rendering the themes list into a `<select>` is the only place theme data reaches JavaScript

### The theme contract
Every theme must satisfy, and review enforces:
1. A visible focus indicator on every interactive element, including controls whose native input is visually replaced (the toggle switches need an explicit `input:focus-visible + .slider` rule)
2. WCAG AA contrast for all text, including over a white photograph for anything drawn on the frame
3. A `prefers-reduced-motion: reduce` block that stops decorative motion, while leaving user-configured slideshow transitions alone
4. A layout that holds under 768px: either an explicit `@media` block, or a documented reliance on the fluid scaffolding in base.css (Classic relies on the percentage widths and centred fixed bars in base.css and ships no media query of its own)
5. Consumption of `--progress` (set by `main.js` as a 0 to 1 number on `#progress-bar`), or deliberate omission of a progress indicator
6. One accent hue and one corner-radius scale
7. No theme-dependent JavaScript

### Hooks available to themes
Theme-neutral signals `main.js` provides for every theme; a theme may use or ignore each one:
- `--progress` on `#progress-bar`: a 0 to 1 number, updated on a 100-step interval per photo
- `body.photo-changed`: replayed (removed, reflowed, re-added) each time a new photo is shown, after its photo date is in place, so `body.photo-changed #bottom-bar { animation: ... }` restarts on every photo
- Corner toasts (`.task-toast`, `.rate-limit-toast`, `.app-toast`) are placed and stacked by `base.css`; JavaScript only toggles their visibility, so a theme styles them with ordinary selectors

### Theme fonts
Each theme owns its typefaces (the icon font is shared). Faces are vendored from pinned `@fontsource/*` npm packages by `make vendor-assets`, which copies the Latin `woff2` files listed in `FONT_FACES` in `scripts/vendor_assets.sh`, plus each family's OFL license, into `static/fonts/<family>/`. The theme stylesheet declares its own `@font-face` rules with `font-display: swap`. Faces needed before first paint go in the theme's `preload_fonts`, which the template emits as `<link rel="preload" as="font" crossorigin>` ahead of the stylesheets.

### Adding a theme
1. Add a CSS file under `static/css/` with the theme's colors, type, radii, and shadows, styled against the shared markup in `templates/index.html` (the element ids, classes, and `data-*` hooks `main.js` reads; a theme never changes the template)
2. Add a `Theme` subclass under `smplfrm/themes/` declaring `id`, `label`, `description`, and `stylesheet`, plus `preload_fonts` if it uses webfonts
3. Add the class to `THEME_REGISTRY` in `smplfrm/themes/__init__.py`
4. If the theme uses webfonts, add its faces to `FONT_FACES` in `scripts/vendor_assets.sh`, pin the `@fontsource/*` package in `package.json`, and run `make vendor-assets`
5. Add a row to the theme table in this document

No migration, no template change, no JavaScript change, and no API change: the theme appears in `GET /api/v1/themes` and the Display tab dropdown because both are generated from the registry.

### Retiring a theme
Delete its CSS file and its registry entry, and remove any faces only it uses from `FONT_FACES` and `static/fonts/`. Configs still storing that theme's id resolve to the default theme through `resolve()`'s fallback, with a logged warning, rather than rendering unstyled.

| Theme id | Label | Status |
|----------|-------|--------|
| `classic` | Classic | Default |
| `gallery` | Gallery | Beta: opt-in |

## API Conventions
- REST API under `/api/v1/`
- PUT for all updates (no PATCH)
- Plugin APIs under `/api/v1/plugins/{name}/`
- Pagination: 5 per page for list endpoints
