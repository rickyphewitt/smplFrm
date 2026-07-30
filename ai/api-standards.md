# API Standards

## Profile

This project implements **JSON:API 1.1 with a documented PUT deviation**. Never claim unqualified JSON:API compliance. The profile is implemented with `djangorestframework-jsonapi==8.1.0`.

## Core Rules

### Media Negotiation
- JSON endpoints use `Content-Type: application/vnd.api+json` for responses and request bodies
- Clients must send `Accept: application/vnd.api+json` (or compatible) for JSON endpoints
- Set `Content-Type` only when a request body exists
- Protocol-exempt endpoints (binary, OAuth, redirect, HTML, empty 204) bypass JSON:API negotiation

### Resource Documents
- Successful responses use top-level `data` — never bare objects, `results` envelopes, or legacy formats
- Resource `id` is the existing 16-character `external_id` serialized as a string
- Singleton resources use an approved stable string ID (e.g., `"current"`)
- Related resources appear only under `relationships` as identifier-only linkage: `{"type": "...", "id": "..."}`
- Never emit top-level `included` (compound documents not supported)
- Never duplicate relationship data under `attributes`

### Complete PUT (No PATCH)
- All updates require a complete resource representation via `PUT`
- `PATCH` is not implemented — return `405 Method Not Allowed`
- Request must include `type`, `id`, and all writable attributes
- Reject unknown members, type/id mismatches, and partial representations

### Strict Query Policy
- Reject with `400`: `include`, `fields[...]`, `sort`, unknown parameters, raw ORM lookups, legacy filter spellings after migration
- Accept only: `page[number]` and explicitly approved `filter[field]` equality parameters per route
- Custom parameters allowed only when semantically unsuitable as filters and explicitly approved in the manifest
- Validation runs before any domain/queryset access

### Pagination
- All collections use server-controlled `page[number]` pagination
- Page size: `SMPL_FRM_API_PAGE_SIZE` environment variable, default `5`, positive integer only
- Clients cannot override page size
- Responses include `links` (first/last/next/prev) and `meta.pagination` (page/pages/count)
- Pagination links preserve only approved query parameters

### Error Responses
- Failing endpoints return top-level `errors` array — never `data`
- Error objects include: `status` (string), `code` (stable identifier), `detail` (sanitized), `source` (where applicable)
- Never expose: raw exceptions, filesystem paths, database schema, SQL, tokens, secrets, stack traces
- Every view method calling service code must catch `Exception`, log exactly once at `ERROR` with `exc_info=True`, and return the generic mapped `500`
- `TaskReportingService` paths use `fail_task(generic_message, exception=e)` as the sole logger — never double-log

### Filters
- Equality-only via `filter[field]` syntax on explicitly approved fields per endpoint
- No arbitrary ORM lookup expressions
- No legacy filter spellings (e.g., `image__external_id`) after that route's atomic migration

## Service Boundaries

- Views validate protocol concerns and delegate domain work to application services or plugin interfaces
- Views must not: mutate models directly, perform raw queryset filtering, dispatch Celery tasks, import plugin internals
- Existing service-layer violations must be remediated under failing tests before migrating that endpoint
- Plugin views call declared plugin-domain ports; core views call application services

## Plugin API Requirements

Plugins registering routes under `/api/v1/plugins/{name}/` must either:
1. Inherit the shared JSON:API profile (parser, renderer, serializer, strict queries, pagination, errors)
2. Declare an explicit exemption in the route contract manifest with an approved reason

Plugin business logic remains self-contained for future extraction. Core code depends only on declared registration/domain interfaces.

## Protocol Exemptions

These routes retain their native protocol:
- **Binary image delivery** (`/api/v1/images/{id}/display`): `image/jpeg`, existing resize parameters, dimension bounds, cache behavior
- **OAuth callbacks** (`/api/v1/plugins/spotify/callback`): code/state exchange, redirects, HTML recovery
- **Empty `204` responses**: delete confirmations and similar

Exempt routes are classified in the contract manifest and validated by route-complete CI.

## Naming Conventions

- Route spelling and JSON:API `type` spelling are independent explicit fields
- Preserve existing route paths for compatibility unless an approved checkpoint records migration handling
- Retain `snake_case` attribute names unless a family checkpoint approves a justified breaking change
- Resource `type` values use plural lowercase (e.g., `images`, `tasks`, `configs`, `plugins`)

## Atomic Migration

- Backend payload change, frontend client behavior, UI consumer, mocks, and tests ship together in the same branch
- Never split a payload migration across merge boundaries
- The shipped UI must remain operational after every merge
- Each top-level task is one feature branch, one reviewed PR, one squash commit

## Configuration

- `SMPL_FRM_API_PAGE_SIZE`: positive integer, default `5`; empty/nonnumeric/zero/negative fails startup with safe message
- Global JSON:API parser/renderer/pagination/exception handling enabled only after all JSON endpoints migrate
- Narrow route overrides retained only for manifest-classified exemptions

## Contract Manifest

Every `/api/v1/` route and method must be classified in the contract manifest as either a JSON endpoint or protocol exemption. Route-complete CI (`make test-api-contract`) fails for unclassified or nonconforming routes.

## Performance

- Each endpoint family defines measurable query-count and latency budgets before migration
- Exceeding approved thresholds blocks release unless remediated or explicitly risk-approved
- Strict query validation runs before expensive domain/provider work
- Collection serializers must avoid N+1 queries

## Observability

- Emit sanitized bounded-cardinality telemetry for unexpected failures, negotiation failures, query rejections, throttling, and OAuth callback failures
- Telemetry excludes: secrets, tokens, personal data, paths, exception text, traceback, raw request/response bodies
- Diagnostic logging (exactly-once `ERROR` with traceback) is separate from telemetry
