# API Design Checklist

## Resource Design

- [ ] Resources are nouns, not verbs ('/users' not '/getUsers')
- [ ] Plural names for collections ('/users' not '/user')
- [ ] Consistent naming across all endpoints (kebab-case)
- [ ] Clear resource hierarchy (avoid deep nesting >2 levels)
- [ ] All CRUD operations properly mapped to HTTP methods
- [ ] Hierarchical for relationships (`/users/{id}/orders`)
- [ ] Versioned (`/v1/`, `/v2/`)

## HTTP Semantics

- [ ] GET for retrieval only (no side effects; safe, idempotent)
- [ ] POST for creation (returns 201 + Location)
- [ ] PUT for full replacement (idempotent)
- [ ] PATCH for partial updates
- [ ] DELETE for removal (idempotent)

## Status Codes

- [ ] `200 OK`: Successful GET, PATCH, PUT
- [ ] `201 Created`: Successful POST
- [ ] `204 No Content`: Successful DELETE
- [ ] `400 Bad Request`: Malformed request
- [ ] `401 Unauthorized`: Authentication required
- [ ] `403 Forbidden`: Authenticated but not authorized
- [ ] `404 Not Found`: Resource doesn't exist
- [ ] `409 Conflict`: State conflict (duplicate email, etc.)
- [ ] `422 Unprocessable Entity`: Validation errors
- [ ] `429 Too Many Requests`: Rate limited
- [ ] `500 Internal Server Error`: Server error
- [ ] `503 Service Unavailable`: Temporary downtime or server issues

## Pagination

- [ ] All collection endpoints paginated
- [ ] Default page size defined (e.g., 20)
- [ ] Maximum page size enforced (e.g., 100)
- [ ] Pagination metadata included (total, pages, etc.)
- [ ] Cursor-based or offset-based pattern chosen

## Filtering & Sorting

- [ ] Query parameters for filtering
- [ ] Sort parameter supported
- [ ] Search parameter for full-text search
- [ ] Field selection supported (sparse fieldsets)

## Versioning

- [ ] Versioning strategy defined (URL/header/query)
- [ ] Version included in all endpoints
- [ ] Deprecation policy documented

## Request Handling

- [ ] Validation with `@Valid`
- [ ] Clear error messages for validation failures
- [ ] Request DTOs (not entities)
- [ ] Reasonable size limits

## Response Design

- [ ] Response DTOs (not entities)
- [ ] Consistent structure across endpoints
- [ ] Proper status codes (not 200 for errors)

## Error Handling

- [ ] Consistent error format based on RFC 7807 (Problem Details)
- [ ] Machine-readable error codes
- [ ] Human-readable messages
- [ ] No stack traces exposed
- [ ] Proper 4xx vs 5xx distinction
- [ ] Detailed error messages
- [ ] Field-level validation errors
- [ ] Error codes for client handling
- [ ] Timestamps in error responses

## Compatibility

- [ ] No breaking changes in current version
- [ ] Deprecated endpoints documented
- [ ] Migration path for breaking changes
