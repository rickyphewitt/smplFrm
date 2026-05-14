# Environment Variables

Environment variables seed the initial configuration on first startup. After that, most settings can be managed through the [Settings](Settings) modal.

## Application

| Name | Default | Description |
|------|---------|-------------|
| `SMPL_FRM_LIBRARY_DIRS` | `<settings.py-dir>/../../library` | Comma-separated list of photo directory paths. |
| `SMPL_FRM_IMAGE_FORMATS` | `jpg,png` | Comma-separated list of image file extensions to scan. |
| `SMPL_FRM_IMAGE_REFRESH_INTERVAL` | `30000` | How long to display each image (milliseconds). |
| `SMPL_FRM_IMAGE_TRANSITION_INTERVAL` | `10000` | Transition duration between images (milliseconds). |
| `SMPL_FRM_EXTERNAL_PORT` | `8321` | Set when the external port differs from the server port. |
| `SMPL_FRM_HOST` | `localhost` | Hostname for the application. |
| `SMPL_FRM_PROTOCOL` | `http://` | Set to `https://` for SSL. |
| `SMPL_FRM_DISPLAY_DATE` | `True` | Show photo date overlay. |
| `SMPL_FRM_FORCE_DATE_FROM_PATH` | `True` | Use file path (`YYYY/MM`) for photo date instead of EXIF. |
| `SMPL_FRM_DISPLAY_CLOCK` | `True` | Show current date and time. |
| `SMPL_FRM_DISPLAY_WEATHER` | `True` | Display the weather. |
| `SMPL_FRM_TIMEZONE` | `America/Los_Angeles` | IANA timezone identifier. |
| `SMPL_FRM_IMAGE_CACHE_TIMEOUT` | `300` | Seconds until a cached image is evicted. |
| `SMPL_FRM_IMAGE_FILL_MODE` | `blur` | Aspect ratio fill: `blur`, `border`, or `zoom_to_fill`. |
| `SMPL_FRM_IMAGE_ZOOM_EFFECT` | `True` | Enable slow zoom animation on images. |
| `SMPL_FRM_IMAGE_TRANSITION_TYPE` | `random` | Transition effect: `fade`, `slide-left`, `slide-right`, `zoom`, `none`, or `random`. |

## Infrastructure

| Name | Default | Description |
|------|---------|-------------|
| `DJANGO_SECRET_KEY` | insecure dev key | Django secret key used for cryptographic signing. Falls back to a dev-only insecure default when unset. **Set this in production.** |
| `REDIS_HOST` | `localhost` | Hostname of the Redis service. In Docker, set to the compose service name (e.g. `cache`). |
| `PYTHONUNBUFFERED` | — | Set to `1` for real-time log output. Recommended for Docker. |

### Generating a secret key

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## Security

| Name | Default | Description |
|------|---------|-------------|
| `SMPL_FRM_THROTTLE_ANON_RATE` | `500/minute` | Global rate limit for anonymous API requests |
| `SMPL_FRM_THROTTLE_USER_RATE` | `120/minute` | Global rate limit for authenticated API requests |
| `SMPL_FRM_THROTTLE_TASK_RATE` | `10/minute` | Global rate limit for task creation endpoint |

Format: `{number}/{period}` where period is `second`, `minute`, `hour`, or `day`.

### Behavior notes

- **Global bucket**: Rate limiting uses a single shared counter across all clients (not per-IP). All anonymous requests share one bucket, all authenticated requests share another, and all task creation requests share a third.
- **HTTP 429 + Retry-After**: When a limit is exceeded, the API returns HTTP 429 (Too Many Requests) with a `Retry-After` header indicating the number of seconds to wait before retrying.
- **Fail-open**: If Redis is unavailable, the throttle system allows requests through rather than blocking all traffic.
- **Invalid value fallback**: If an environment variable contains an invalid format, the system falls back to the default rate and logs a warning. Check application logs for configuration warnings at startup.
- **UI resilience**: When the frame UI receives a 429 response, it automatically retries with backoff (up to 3 attempts) and displays a subtle informational toast. The current image, Spotify data, and task progress remain visible during rate limiting. If the toast appears frequently, increase `SMPL_FRM_THROTTLE_ANON_RATE`.

## Plugins

Plugin env vars use the prefix `SMPL_FRM_PLUGINS_{PLUGIN_NAME}_`. These override plugin DB settings on every startup.

### Spotify

| Name | Default | Description |
|------|---------|-------------|
| `SMPL_FRM_PLUGINS_SPOTIFY_CLIENT_ID` | — | Spotify API client ID. See [Spotipy docs](https://spotipy.readthedocs.io/en/latest/#getting-started). |
| `SMPL_FRM_PLUGINS_SPOTIFY_CLIENT_SECRET` | — | Spotify API client secret. Redirect URI must match `{SMPL_FRM_PROTOCOL}{SMPL_FRM_HOST}:{SMPL_FRM_EXTERNAL_PORT}/api/v1/plugins/spotify/callback`. |

### Weather

| Name | Default | Description |
|------|---------|-------------|
| `SMPL_FRM_PLUGINS_WEATHER_COORDS` | `63.1786,-147.4661` | Lat,Long for weather location. [Weather data by Open-Meteo.com](https://open-meteo.com) |
| `SMPL_FRM_PLUGINS_WEATHER_TEMP_UNIT` | `F` | `F` for Fahrenheit, `C` for Celsius. |
| `SMPL_FRM_PLUGINS_WEATHER_PRECIP_UNIT` | `in` | `in` for inches, `mm` for millimeters. |
| `SMPL_FRM_PLUGINS_WEATHER_WINDSPEED_UNIT` | `mph` | `kmh`, `kn`, `ms`, or `mph`. |
