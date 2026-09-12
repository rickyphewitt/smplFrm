# API Standard

smplFrm exposes a REST API under `/api/v1/` following **JSON:API 1.1 with a documented PUT deviation**.

**NOTE: These API standards are for internal API's used by the smplFrm frontend and not intended for external api client use. Breaking changes will occur without warning.**


## Profile Summary

- **Specification basis:** [JSON:API 1.1](https://jsonapi.org/format/1.1/)
- **Deviation:** Updates use complete-representation `PUT` instead of JSON:API `PATCH`. This is a deliberate design choice — partial updates are not supported.
- **Media type:** `application/vnd.api+json` for all JSON endpoint requests and responses
- **Base path:** `/api/v1/` (preserved across the migration)

## Resource Identity

Every persisted resource uses its existing 16-character alphanumeric `external_id` as the JSON:API `id` field, serialized as a string. Singleton resources (e.g., current weather, current playback state) use an approved stable string identifier.

## Document Structure

### Successful Responses

```json
{
  "data": {
    "type": "images",
    "id": "aBcDeFgHiJkLmNoP",
    "attributes": {
      "name": "sunset.jpg",
      "view_count": 3
    },
    "relationships": {
      "image": {
        "data": { "type": "images", "id": "aBcDeFgHiJkLmNoP" }
      }
    }
  }
}
```

### Collections (Paginated)

```json
{
  "data": [...],
  "links": {
    "first": "/api/v1/images?page[number]=1",
    "last": "/api/v1/images?page[number]=4",
    "next": "/api/v1/images?page[number]=2",
    "prev": null
  },
  "meta": {
    "pagination": {
      "page": 1,
      "pages": 4,
      "count": 20
    }
  }
}
```

### Error Responses

```json
{
  "errors": [
    {
      "status": "400",
      "code": "invalid_query_parameter",
      "detail": "The query parameter 'sort' is not supported.",
      "source": { "parameter": "sort" }
    }
  ]
}
```

## Complete PUT Updates

All mutable resources require a **complete resource representation** via `PUT`. The request body must include all writable attributes. `PATCH` is not implemented and returns `405 Method Not Allowed`.

```http
PUT /api/v1/configs/aBcDeFgHiJkLmNoP
Content-Type: application/vnd.api+json

{
  "data": {
    "type": "configs",
    "id": "aBcDeFgHiJkLmNoP",
    "attributes": {
      "name": "My Config",
      "description": "Custom settings",
      "display_date": true,
      "display_clock": true,
      ...
    }
  }
}
```

## Media Negotiation

- JSON endpoints require `Accept: application/vnd.api+json` (or compatible)
- Request bodies must use `Content-Type: application/vnd.api+json`
- Exempt endpoints (binary, OAuth) use their native media types

## Strict Query Policy

The API enforces a closed query surface:

- **Supported:** `page[number]`, explicitly approved `filter[field]` parameters per route
- **Rejected with 400:** `include`, `fields[...]`, `sort`, unknown parameters, raw ORM lookups

No client-controlled page size. The server uses `SMPL_FRM_API_PAGE_SIZE` (default: 5).

## Pagination

All resource collections use server-controlled `page[number]` pagination:

- Page size is fixed at `SMPL_FRM_API_PAGE_SIZE` (default: 5, positive integer, environment-configurable)
- Clients cannot override page size
- Response includes `links` (first/last/next/prev) and `meta.pagination` (page/pages/count)

## Relationships

Related resources are expressed as identifier-only linkage objects:

```json
"relationships": {
  "image": {
    "data": { "type": "images", "id": "aBcDeFgHiJkLmNoP" }
  }
}
```

- No `included` compound documents (never emitted)
- No inline embedding of related objects
- Related data is never duplicated under `attributes`

## Error Handling

- All JSON endpoint errors return a top-level `errors` array (never `data`)
- Error objects include: `status` (string), `code` (stable identifier), `detail` (safe message), `source` (where applicable)
- No raw exceptions, filesystem paths, database details, tokens, or secrets in error responses
- Unexpected server errors return a generic `500` with a stable code

## Protocol Exemptions

The following routes retain their native protocol and bypass JSON:API negotiation:

| Route | Protocol | Reason |
|-------|----------|--------|
| `/api/v1/images/{id}/display` | Binary `image/jpeg` | Frame image delivery with resize parameters |
| `/api/v1/plugins/spotify/callback` | OAuth2 redirect/HTML | OAuth code/state exchange and error recovery |
| Any `204` response | Empty body | Delete confirmations and similar |

## Plugin Author Obligations

Plugins registering API routes under `/api/v1/plugins/{name}/` must either:
1. **Inherit** the shared JSON:API profile (parser, renderer, serializer conventions, strict queries, pagination, errors), or
2. **Declare an explicit exemption** in the route contract manifest with an approved reason and expected protocol

Plugin-specific business logic must remain self-contained behind declared interfaces. Core code must not import plugin internals.

## Filters

Filtering uses equality-only `filter[field]` syntax on approved fields per endpoint:

```
GET /api/v1/images_metadata?filter[image]=aBcDeFgHiJkLmNoP
```

No arbitrary ORM lookups, no legacy filter spellings after migration cutover.

## Custom Actions

Some endpoints expose non-CRUD actions:

| Route | Method | Description |
|-------|--------|-------------|
| `/api/v1/configs/apply` | POST | Apply active preset to new custom config |
| `/api/v1/configs/{id}/activate` | POST | Activate a specific config |
| `/api/v1/images/next` | GET | Select next image for display |

Custom actions return standard JSON:API resource documents.

## Resources

### Tasks

Background operations (library rescanning, cache clearing, image count reset) are exposed as **polymorphic task resources**. The task type becomes the JSON:API `type` field, enabling type-specific behavior in future versions.

**Endpoint:** `/api/v1/tasks`

**Polymorphic Types:**
| Type | Description |
|------|-------------|
| `rescan_library_tasks` | Rescan photo library directories |
| `clear_cache_tasks` | Clear cached image data |
| `reset_image_count_tasks` | Reset image view counts |

#### Create Task (POST)

```http
POST /api/v1/tasks
Content-Type: application/vnd.api+json

{
  "data": {
    "type": "rescan_library_tasks",
    "attributes": {}
  }
}
```

**Response (201 Created):**
```json
{
  "data": {
    "type": "rescan_library_tasks",
    "id": "aBcDeFgHiJkLmNoP",
    "attributes": {
      "label": "Rescan Library",
      "status": "pending",
      "progress": 0,
      "error": "",
      "created": "2026-08-05T10:30:00Z"
    }
  }
}
```

**Error Responses:**
- `409 Conflict` — A task of this type is already pending or running
- `409 Conflict` — Invalid task type (type not in accepted list)
- `500 Internal Server Error` — Server error during task creation

#### Get Task (GET)

```http
GET /api/v1/tasks/aBcDeFgHiJkLmNoP
Accept: application/vnd.api+json
```

**Response (200 OK):**
```json
{
  "data": {
    "type": "rescan_library_tasks",
    "id": "aBcDeFgHiJkLmNoP",
    "attributes": {
      "label": "Rescan Library",
      "status": "running",
      "progress": 45,
      "error": "",
      "created": "2026-08-05T10:30:00Z"
    }
  }
}
```

**Error Responses:**
- `403 Forbidden` — Task not found (prevents ID enumeration)

#### List Tasks (GET)

```http
GET /api/v1/tasks?page[number]=1
Accept: application/vnd.api+json
```

**Response (200 OK):**
```json
{
  "data": [
    {
      "type": "rescan_library_tasks",
      "id": "aBcDeFgHiJkLmNoP",
      "attributes": {
        "label": "Rescan Library",
        "status": "completed",
        "progress": 100,
        "error": "",
        "created": "2026-08-05T10:30:00Z"
      }
    },
    {
      "type": "clear_cache_tasks",
      "id": "qRsTuVwXyZaBcDeF",
      "attributes": {
        "label": "Clear Cache",
        "status": "failed",
        "progress": 30,
        "error": "Disk write error",
        "created": "2026-08-05T09:15:00Z"
      }
    }
  ],
  "links": {
    "first": "/api/v1/tasks?page[number]=1",
    "last": "/api/v1/tasks?page[number]=2",
    "next": "/api/v1/tasks?page[number]=2",
    "prev": null
  },
  "meta": {
    "pagination": {
      "page": 1,
      "pages": 2,
      "count": 8
    }
  }
}
```

#### Delete Task (DELETE)

```http
DELETE /api/v1/tasks/aBcDeFgHiJkLmNoP
```

**Response:** `204 No Content`

**Error Responses:**
- `403 Forbidden` — Task not found (prevents ID enumeration)

#### Task Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `label` | string | Human-readable task type label for UI display |
| `status` | string | One of: `pending`, `running`, `completed`, `failed` |
| `progress` | integer | Completion percentage (0-100) |
| `error` | string | Error message if status is `failed`, empty otherwise |
| `created` | datetime | ISO 8601 creation timestamp |

#### Notes

- Tasks are **read-only** after creation — `PUT` and `PATCH` return `405 Method Not Allowed`
- Only one task per type can be `pending` or `running` at a time
- Tasks are soft-deleted and retained for history
- Rate limiting: `SMPL_FRM_THROTTLE_TASK_RATE` (default: `10/minute`)



### Images

Image resources represent photos in the library. Images are read-only through the API.

**Endpoint:** `/api/v1/images`

#### List Images (GET)

```http
GET /api/v1/images?page[number]=1
Accept: application/vnd.api+json
```

**Response (200 OK):**
```json
{
  "data": [
    {
      "type": "images",
      "id": "aBcDeFgHiJkLmNoP",
      "attributes": {
        "name": "sunset.jpg",
        "file_name": "sunset.jpg",
        "created": "2026-08-05T10:30:00Z",
        "updated": "2026-08-05T10:30:00Z",
        "view_count": 42
      }
    }
  ],
  "links": {
    "first": "/api/v1/images?page[number]=1",
    "last": "/api/v1/images?page[number]=10",
    "next": "/api/v1/images?page[number]=2",
    "prev": null
  },
  "meta": {
    "pagination": {
      "page": 1,
      "pages": 10,
      "count": 50
    }
  }
}
```

#### Get Image (GET)

```http
GET /api/v1/images/aBcDeFgHiJkLmNoP
Accept: application/vnd.api+json
```

**Response (200 OK):**
```json
{
  "data": {
    "type": "images",
    "id": "aBcDeFgHiJkLmNoP",
    "attributes": {
      "name": "sunset.jpg",
      "file_name": "sunset.jpg",
      "created": "2026-08-05T10:30:00Z",
      "updated": "2026-08-05T10:30:00Z",
      "view_count": 42
    }
  }
}
```

**Error Responses:**
- `403 Forbidden` — Image not found (prevents ID enumeration)

#### Next Image (GET)

Select the next image for display cycling and preload upcoming images.

```http
GET /api/v1/images/next?width=1920&height=1080
Accept: application/vnd.api+json
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `width` | integer | 100 | Target display width in pixels |
| `height` | integer | 100 | Target display height in pixels |

**Response (200 OK):**
```json
{
  "data": {
    "type": "images",
    "id": "aBcDeFgHiJkLmNoP",
    "attributes": {
      "name": "sunset.jpg",
      "file_name": "sunset.jpg",
      "created": "2026-08-05T10:30:00Z",
      "updated": "2026-08-05T10:30:00Z",
      "view_count": 42
    }
  }
}
```

**Error Responses:**
- `400 Bad Request` — Invalid dimension parameters (non-numeric, zero, negative, or exceeds max)
- `404 Not Found` — No images available in library

#### Display Image (GET) — Protocol Exempt

Returns binary image data for display. **Not a JSON:API endpoint.**

```http
GET /api/v1/images/aBcDeFgHiJkLmNoP/display?width=1920&height=1080
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `width` | integer | 100 | Target width in pixels |
| `height` | integer | 100 | Target height in pixels |

**Response (200 OK):**
- Content-Type: `image/jpeg`
- Body: Binary image data

**Error Responses:**
- `400 Bad Request` — Invalid dimension parameters
- `404 Not Found` — Image file not found on disk

#### Image Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | string | Display name of the image |
| `file_name` | string | Original filename |
| `created` | datetime | ISO 8601 creation timestamp |
| `updated` | datetime | ISO 8601 last update timestamp |
| `view_count` | integer | Number of times image has been displayed |

#### Notes

- Images are **read-only** — `POST`, `PUT`, `PATCH`, `DELETE` return `405 Method Not Allowed`
- `file_path` is intentionally excluded from responses for security
- View count is incremented each time `/display` is called
- The `/next` endpoint triggers background caching of upcoming images
