# API Standard

smplFrm exposes a REST API under `/api/v1/` following **JSON:API 1.1 with a documented PUT deviation**.

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

