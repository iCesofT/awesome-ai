---
name: api-design
description: Design and review REST APIs for resource modeling, HTTP semantics, response consistency, pagination, versioning, backward compatibility, and production readiness.
metadata:
  version: "1.2.0"
  domain: architecture
  triggers: API design, REST API, API review, API contract, endpoint design, URL naming, HTTP methods, status codes, pagination, versioning, backward compatibility, rate limiting
  role: architect
  scope: design
---

# API Design and Contract Review

Design and audit REST APIs for correctness, consistency, and compatibility.

## When to Use

- Designing new API endpoints or resource models
- Reviewing existing API contracts before release
- Checking HTTP semantics, status codes, and URL conventions
- Adding pagination, filtering, sorting, or search
- Defining versioning and backward compatibility strategy
- Standardizing error responses for public or partner-facing APIs

## Quick Reference: Common Issues

| Issue | Symptom | Impact |
|-------|---------|--------|
| Wrong HTTP verb | POST for retrieval or GET for state change | Confusion, caching bugs, non-RESTful behavior |
| Missing versioning | `/api/users` instead of `/api/v1/users` | Breaking changes affect all clients |
| Entity leak | ORM/JPA entity returned directly | Exposes internals, lazy-loading and N+1 risk |
| 200 with error body | Success status with failure payload | Breaks client error handling |
| Inconsistent naming | `/getUsers` vs `/users` | Harder to learn and document |
| Unpaginated collections | `findAll()` exposed directly | Performance and payload issues |

## Resource Design

### URL Structure

```
# Resources are nouns, plural, lowercase, kebab-case
GET    /api/v1/users
GET    /api/v1/users/:id
POST   /api/v1/users
PUT    /api/v1/users/:id
PATCH  /api/v1/users/:id
DELETE /api/v1/users/:id

# Sub-resources for relationships
GET    /api/v1/users/:id/orders
POST   /api/v1/users/:id/orders

# Actions that don't map to CRUD (use verbs sparingly)
POST   /api/v1/orders/:id/cancel
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
```

### Naming Rules

```
# GOOD
/api/v1/team-members
/api/v1/orders?status=active
/api/v1/users/123/orders

# BAD
/api/v1/getUsers
/api/v1/user
/api/v1/team_members
/api/v1/users/123/getOrders
```

## HTTP Semantics

### Method Selection Guide

| Method | Idempotent | Safe | Use For |
|--------|-----------|------|---------|
| GET | Yes | Yes | Retrieve resources |
| POST | No | No | Create resources, trigger actions |
| PUT | Yes | No | Full replacement of a resource |
| PATCH | No* | No | Partial update of a resource |
| DELETE | Yes | No | Remove resource |

*PATCH can be idempotent depending on implementation.

### Common Mistakes

```java
// BAD: POST for retrieval
@PostMapping("/users/search")
public List<User> searchUsers(@RequestBody SearchCriteria criteria) { }

// GOOD: GET with query params (or POST only if criteria is very complex)
@GetMapping("/users")
public List<User> searchUsers(
    @RequestParam String name,
    @RequestParam(required = false) String email) { }

// BAD: GET for state change
@GetMapping("/users/{id}/activate")
public void activateUser(@PathVariable Long id) { }

// GOOD: POST or PATCH for state change
@PostMapping("/users/{id}/activate")
public ResponseEntity<Void> activateUser(@PathVariable Long id) { }

// BAD: POST for idempotent update
@PostMapping("/users/{id}")
public User updateUser(@PathVariable Long id, @RequestBody UserDto dto) { }

// GOOD: PUT for full replacement, PATCH for partial update
@PutMapping("/users/{id}")
public User replaceUser(@PathVariable Long id, @RequestBody UserDto dto) { }

@PatchMapping("/users/{id}")
public User updateUser(@PathVariable Long id, @RequestBody UserPatchDto dto) { }
```

## Status Codes and Error Semantics

### Status Code Reference

```
# Success
200 OK                    — GET, PUT, PATCH with response body
201 Created               — POST when a resource is created; include Location header
204 No Content            — DELETE or successful update with no body

# Client Errors
400 Bad Request           — Malformed JSON, invalid input shape
401 Unauthorized          — Missing or invalid authentication
403 Forbidden             — Authenticated but not allowed
404 Not Found             — Resource doesn't exist
409 Conflict              — Duplicate or state conflict
422 Unprocessable Entity  — Valid syntax, semantically invalid data
429 Too Many Requests     — Rate limit exceeded

# Server Errors
500 Internal Server Error — Unexpected failure, never expose internals
502 Bad Gateway           — Upstream dependency failed
503 Service Unavailable   — Temporary overload, include Retry-After when useful
```

### Anti-Patterns

```json
{ "status": 200, "success": false, "error": "Not found" }
```

```http
HTTP/1.1 404 Not Found
Content-Type: application/json

{ "error": { "code": "not_found", "message": "User not found" } }
```

```java
// BAD: 200 with error body
@GetMapping("/{id}")
public ResponseEntity<Map<String, Object>> getUser(@PathVariable Long id) {
    try {
        User user = userService.findById(id);
        return ResponseEntity.ok(Map.of("status", "success", "data", user));
    } catch (NotFoundException e) {
        return ResponseEntity.ok(Map.of(
            "status", "error",
            "message", "User not found"
        ));
    }
}

// GOOD: proper status code
@GetMapping("/{id}")
public ResponseEntity<UserResponse> getUser(@PathVariable Long id) {
    return userService.findById(id)
        .map(ResponseEntity::ok)
        .orElse(ResponseEntity.notFound().build());
}
```

## Request and Response Design

### DTOs, Not Entities

```java
// BAD: Entity in response leaks internals
@GetMapping("/{id}")
public User getUser(@PathVariable Long id) {
    return userRepository.findById(id).orElseThrow();
}

// GOOD: DTO response controls public contract
@GetMapping("/{id}")
public UserResponse getUser(@PathVariable Long id) {
    User user = userService.findById(id);
    return UserResponse.from(user);
}
```

### Success Response

```json
{
  "data": {
    "id": "abc-123",
    "email": "alice@example.com",
    "name": "Alice",
    "created_at": "2025-01-15T10:30:00Z"
  }
}
```

### Collection Response

```json
{
  "data": [
    { "id": "abc-123", "name": "Alice" },
    { "id": "def-456", "name": "Bob" }
  ],
  "meta": {
    "total": 142,
    "page": 1,
    "per_page": 20,
    "total_pages": 8
  },
  "links": {
    "self": "/api/v1/users?page=1&per_page=20",
    "next": "/api/v1/users?page=2&per_page=20",
    "last": "/api/v1/users?page=8&per_page=20"
  }
}
```

### Error Response

Error Response is based on the Problem Details for HTTP APIs specification (RFC 7807) with some extensions for validation errors.

```json
{
  "type" : "https://example.com/probs/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "Request validation failed",
  "timestamp": 1672567890123,
  "errors": [
    "email: Must be a valid email address",
    "age: Must be between 0 and 150"
  ]
}
```

### Response Consistency

```java
// BAD: mixed response shapes
@GetMapping("/users")
public List<User> getUsers() { }

@GetMapping("/users/{id}")
public User getUser(@PathVariable Long id) { }

@GetMapping("/users/count")
public int countUsers() { }

// GOOD: consistent envelope or consistent object conventions
@GetMapping("/users")
public ApiResponse<List<UserResponse>> getUsers() {
    return ApiResponse.success(userService.findAll());
}
```

### Error Handling Baseline

```java
@ExceptionHandler(Exception.class)
public ResponseEntity<ProblemDetail> handleAll(Exception ex) {
    log.error("Unexpected error", ex);
    return ResponseEntity.status(500)
        .contentType(MediaType.APPLICATION_PROBLEM_JSON)
        .body(ProblemDetail.forStatusAndDetail(
            HttpStatus.INTERNAL_SERVER_ERROR,
            "An unexpected error occurred"
        ).withType("https://example.com/probs/internal-error")
         .withInstance(URI.create("/api/v1/some-endpoint"))
         .with("code", "internal_error")
         .with("timestamp", Instant.now().toEpochMilli())
        );
}
```

## Pagination

### Offset-Based

```
GET /api/v1/users?page=2&per_page=20

SELECT * FROM users
ORDER BY created_at DESC
LIMIT 20 OFFSET 20;
```

Pros: easy to implement, supports jump to page N.

Cons: slow on large offsets, unstable with concurrent inserts.

### Cursor-Based

```
GET /api/v1/users?cursor=eyJpZCI6MTIzfQ&limit=20

SELECT * FROM users
WHERE id > :cursor_id
ORDER BY id ASC
LIMIT 21;
```

```json
{
  "data": [...],
  "meta": {
    "has_next": true,
    "next_cursor": "eyJpZCI6MTQzfQ"
  }
}
```

Pros: stable performance regardless of position, good for feeds and public APIs.

Cons: cannot jump to arbitrary page, cursor must remain opaque.

### Selection Guide

| Use Case | Pagination Type |
|----------|----------------|
| Admin dashboards, small datasets | Offset |
| Infinite scroll and feeds | Cursor |
| Public APIs | Cursor by default |
| Search results | Offset |

## Filtering, Sorting, and Search

### Filtering

```
GET /api/v1/orders?status=active&customer_id=abc-123
GET /api/v1/products?price[gte]=10&price[lte]=100
GET /api/v1/orders?created_at[after]=2025-01-01
GET /api/v1/products?category=electronics,clothing
GET /api/v1/orders?customer.country=US
```

### Sorting

```
GET /api/v1/products?sort=-created_at
GET /api/v1/products?sort=-featured,price,-created_at
```

### Search and Sparse Fieldsets

```
GET /api/v1/products?q=wireless+headphones
GET /api/v1/users?email=alice
GET /api/v1/users?fields=id,name,email
GET /api/v1/orders?fields=id,total,status&include=customer.name
```

## Authentication, Authorization, and Rate Limiting

### Authentication Headers

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
X-API-Key: sk_live_abc123
```

### Authorization Patterns

```typescript
app.get("/api/v1/orders/:id", async (req, res) => {
  const order = await Order.findById(req.params.id);
  if (!order) return res.status(404).json({ error: { code: "not_found" } });
  if (order.userId !== req.user.id) return res.status(403).json({ error: { code: "forbidden" } });
  return res.json({ data: order });
});

app.delete("/api/v1/users/:id", requireRole("admin"), async (req, res) => {
  await User.delete(req.params.id);
  return res.status(204).send();
});
```

### Rate Limit Contract

```
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640000000
```

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
Content-Type: application/json

{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "Rate limit exceeded. Try again in 60 seconds."
  }
}
```

## Versioning and Compatibility

### Recommended Strategy

```
/api/v1/users
/api/v2/users
```

URL path versioning is the default recommendation because it is explicit, easy to route, and easy to test.

### Versioning Rules

1. Start with `/api/v1/` for public APIs.
2. Maintain at most two active versions.
3. Announce deprecations before removal.
4. Add `Sunset` headers for public API retirement.
5. Return `410 Gone` only after the sunset date.

### Breaking vs Non-Breaking Changes

| Change | Breaking? | Recommended Migration |
|--------|-----------|-----------------------|
| Remove endpoint | Yes | Deprecate first, remove in next version |
| Remove field from response | Yes | Keep field, return null or default temporarily |
| Add required field to request | Yes | Add as optional first with default |
| Change field type | Yes | Introduce new field, deprecate old |
| Rename field | Yes | Support both during migration |
| Add optional query param | No | Safe |
| Add response field | No | Safe |
| Add endpoint | No | Safe |

### Deprecation Example

```java
@RestController
@RequestMapping("/api/v1/users")
public class UserControllerV1 {

    @Deprecated
    @GetMapping("/by-email")
    public UserResponse getByEmailOld(@RequestParam String email) {
        return getByEmail(email);
    }

    @GetMapping(params = "email")
    public UserResponse getByEmail(@RequestParam String email) {
        return userService.findByEmail(email);
    }
}
```

## Implementation Patterns

### TypeScript

```typescript
import { z } from "zod";
import { NextRequest, NextResponse } from "next/server";

const createUserSchema = z.object({
  email: z.string().email(),
  name: z.string().min(1).max(100),
});

export async function POST(req: NextRequest) {
  const body = await req.json();
  const parsed = createUserSchema.safeParse(body);

  if (!parsed.success) {
    return NextResponse.json(
      {
        error: {
          code: "validation_error",
          message: "Request validation failed",
          details: parsed.error.issues.map(issue => ({
            field: issue.path.join("."),
            message: issue.message,
            code: issue.code,
          })),
        },
      },
      { status: 422 },
    );
  }

  const user = await createUser(parsed.data);

  return NextResponse.json(
    { data: user },
    {
      status: 201,
      headers: { Location: `/api/v1/users/${user.id}` },
    },
  );
}
```

### Python

```python
from rest_framework import serializers, status, viewsets
from rest_framework.response import Response


class CreateUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    name = serializers.CharField(max_length=100)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "name", "created_at"]


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return CreateUserSerializer
        return UserSerializer

    def create(self, request):
        serializer = CreateUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = UserService.create(**serializer.validated_data)
        return Response(
            {"data": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
            headers={"Location": f"/api/v1/users/{user.id}"},
        )
```

### Go

```go
func (h *UserHandler) CreateUser(w http.ResponseWriter, r *http.Request) {
    var req CreateUserRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        writeError(w, http.StatusBadRequest, "invalid_json", "Invalid request body")
        return
    }

    if err := req.Validate(); err != nil {
        writeError(w, http.StatusUnprocessableEntity, "validation_error", err.Error())
        return
    }

    user, err := h.service.Create(r.Context(), req)
    if err != nil {
        switch {
        case errors.Is(err, domain.ErrEmailTaken):
            writeError(w, http.StatusConflict, "email_taken", "Email already registered")
        default:
            writeError(w, http.StatusInternalServerError, "internal_error", "Internal error")
        }
        return
    }

    w.Header().Set("Location", fmt.Sprintf("/api/v1/users/%s", user.ID))
    writeJSON(w, http.StatusCreated, map[string]any{"data": user})
}
```

## Review Workflow for Large APIs

1. List controllers and group them by resource.
2. Sample two or three representative controllers to identify conventions.
3. Check global exception handling once before reviewing individual endpoints.
4. Search specifically for entity leaks, unversioned routes, and `200` error responses.

```bash
find . -name "*Controller.java"
grep -r "public.*Entity.*@GetMapping" --include="*.java"
grep -r "ResponseEntity.ok.*error" --include="*.java"
grep -r "@RequestMapping.*api" --include="*.java" | grep -v "/v[0-9]"
```

## Consolidated Checklist

Before shipping or approving an endpoint:

- [ ] Resource URL uses plural nouns, lowercase, and kebab-case
- [ ] HTTP verb matches operation semantics
- [ ] Versioning strategy is explicit for public APIs
- [ ] Request input is validated with schema-based validation
- [ ] DTOs are used instead of persistence entities in the API contract
- [ ] Response shape is consistent across the API
- [ ] Collections are paginated
- [ ] Filtering, sorting, and search parameters are predictable
- [ ] Status codes are semantic and never overload `200 OK`
- [ ] Error responses use stable machine-readable codes
- [ ] Authentication and authorization are enforced correctly
- [ ] Rate limiting contract is documented where applicable
- [ ] Backward compatibility risks are identified before release
- [ ] OpenAPI or equivalent documentation is updated

---

## Related Skills

- `openapi-spec-generation` — Translate API design decisions into OpenAPI 3.x specs and generated Spring Boot code
- `clean-ddd-hexagonal` — REST controllers are the primary inbound adapter in hexagonal architecture
- `springboot-security` — API security: JWT bearer tokens, OAuth2 scopes, endpoint authorization
- `error-handling-patterns` — API error responses follow RFC 9457 ProblemDetail conventions
- `grpc-design` — gRPC is the internal API complement to REST for inter-service communication
