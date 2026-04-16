---
name: java-code-review
description: Systematic code review for Java 25 with null safety, exception handling, concurrency, Virtual Threads, records, sealed classes, pattern matching, coding standards (naming, immutability, project structure), and performance checks.
metadata:
  version: "1.1.0"
  domain: backend
  triggers: code review, Java review, PR review, Java 25, coding standards, naming conventions, immutability, records, Virtual Threads
  role: specialist
  scope: review
---

# Java Code Review Skill

Systematic code review checklist for Java 25 projects, combining review categories with coding standards enforcement.

## When to Use
- User says "review this code" / "check this PR" / "code review"
- Before merging a PR
- After implementing a feature
- Enforcing naming, immutability, or exception handling conventions

## Review Strategy

1. **Quick scan** - Understand intent, identify scope
2. **Standards pass** - Check naming, structure, immutability
3. **Checklist pass** - Go through each category below
4. **Summary** - List findings by severity (Critical → Minor)

## Output Format

```markdown
## Code Review: [file/feature name]

### Critical
- [Issue description + line reference + suggestion]

### Improvements
- [Suggestion + rationale]

### Minor/Style
- [Nitpicks, optional improvements]

### Good Practices Observed
- [Positive feedback - important for morale]
```

---

## Coding Standards

### Naming Conventions

```java
// ✅ Classes/Records: PascalCase
public class MarketService {}
public record Money(BigDecimal amount, Currency currency) {}

// ✅ Methods/fields: camelCase
private final MarketRepository marketRepository;
public Market findBySlug(String slug) {}

// ✅ Constants: UPPER_SNAKE_CASE
private static final int MAX_PAGE_SIZE = 100;

// ✅ Booleans: is/has/can prefix
boolean isActive;
boolean hasPermission;
boolean canProcess;
```

### Immutability First

```java
// ✅ Favor records and final fields
public record MarketDto(Long id, String name, MarketStatus status) {}

public class Market {
    private final Long id;
    private final String name;
    // getters only, no setters
}

// ✅ Immutable collections
List<String> items = List.of("a", "b", "c");
Map<String, String> map = Map.of("key", "value");
```

### Project Structure (Maven)

```
src/main/java/com/example/app/
  config/          ← Spring @Configuration classes
  controller/      ← REST controllers
  service/         ← Business logic
  repository/      ← Data access interfaces
  domain/          ← Domain entities and value objects
  dto/             ← DTOs, request/response records
  util/            ← Stateless utility classes
src/main/resources/
  application.yml
src/test/java/...  ← Mirrors main structure
```

### Member Order Within Class

1. Constants (`static final`)
2. Instance fields
3. Constructors
4. Public methods
5. Protected methods
6. Private methods

---

## Review Checklist

### 1. Java 25 Modern Features

**Records para DTOs/Value Objects:**
```java
// ❌ Clase mutable innecesaria
public class ProductRequest {
    private String name;
    private BigDecimal price;
    // getters, setters, equals, hashCode, toString...
}

// ✅ Record inmutable, compacto
public record ProductRequest(
    @NotBlank String name,
    @DecimalMin("0.0") BigDecimal price
) {}
```

**Pattern Matching para instanceof:**
```java
// ❌ Cast manual redundante
if (shape instanceof Circle) {
    Circle circle = (Circle) shape;
    return circle.radius() * 2;
}

// ✅ Pattern matching (Java 16+)
if (shape instanceof Circle c) {
    return c.radius() * 2;
}
```

**Switch Expressions con Sealed Classes:**
```java
// ✅ Switch exhaustivo con sealed hierarchy
sealed interface Shape permits Circle, Rectangle, Triangle {}

double area = switch (shape) {
    case Circle c    -> Math.PI * c.radius() * c.radius();
    case Rectangle r -> r.width() * r.height();
    case Triangle t  -> 0.5 * t.base() * t.height();
};
// El compilador verifica exhaustividad
```

**Text Blocks (Java 15+):**
```java
// ❌ Fragile concatenation
String sql = "SELECT id, name FROM products " +
             "WHERE status = 'ACTIVE' " +
             "ORDER BY name";

// ✅ Readable text block
String sql = """
    SELECT id, name
    FROM products
    WHERE status = 'ACTIVE'
    ORDER BY name
    """;
```

**Flags:**
- Mutable classes where a `record` would suffice (DTOs, Commands, Value Objects)
- `instanceof` followed by manual cast in Java 16+
- Non-exhaustive switch when sealed types are available
- String concatenation for SQL/JSON (use text blocks)
- Not using `var` for local type inference where it improves readability

### 2. Null Safety

**Check for:**
```java
// ❌ NPE risk
String name = user.getName().toUpperCase();

// ✅ Safe with Optional
String name = Optional.ofNullable(user.getName())
    .map(String::toUpperCase)
    .orElse("");

// ✅ Map/flatMap instead of get()
return marketRepository.findBySlug(slug)
    .map(MarketResponse::from)
    .orElseThrow(() -> new EntityNotFoundException("Market not found"));
```

**Flags:**
- Chained method calls without null checks
- Missing `@Nullable` / `@NonNull` annotations on public APIs
- `Optional.get()` without `isPresent()` check
- Returning `null` from methods that could return `Optional` or empty collection
- Using `@NonNull` without Bean Validation on REST inputs (use `@NotNull` / `@NotBlank`)

**Suggest:**
- `Optional` for return types that may be absent
- `Objects.requireNonNull()` for constructor/method params
- Return empty collections: `List.of()`, `Collections.emptyList()`

### 3. Exception Handling

**Check for:**
```java
// ❌ Swallowing exceptions
try {
    process();
} catch (Exception e) {
    // silently ignored
}

// ❌ Losing stack trace
catch (IOException e) {
    throw new RuntimeException(e.getMessage());
}

// ✅ Proper handling
catch (IOException e) {
    log.error("Failed to process file: {}", filename, e);
    throw new ProcessingException("File processing failed", e);
}
```

**Domain-specific exceptions (preferred):**
```java
// ✅ Meaningful domain exception
public class MarketNotFoundException extends RuntimeException {
    public MarketNotFoundException(String slug) {
        super("Market not found: " + slug);
    }
}

throw new MarketNotFoundException(slug);
```

**Flags:**
- Empty catch blocks
- Catching `Exception` or `Throwable` broadly
- Losing original exception (not chaining)
- Using exceptions for flow control
- Checked exceptions leaking through API boundaries

### 4. Virtual Threads (Java 25 / Spring Boot 4)

```java
// ✅ Correct: Virtual Threads for I/O-bound tasks
try (ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor()) {
    executor.submit(() -> callExternalApi(request));
}

// ❌ Anti-pattern: ThreadLocal with Virtual Threads
private static final ThreadLocal<User> currentUser = new ThreadLocal<>();

// ✅ ScopedValue (Java 21+) for propagated context
private static final ScopedValue<User> CURRENT_USER = ScopedValue.newInstance();
ScopedValue.where(CURRENT_USER, user).run(() -> processRequest());

// ❌ synchronized with blocking operations
// In Java 25 (JEP 491) no longer causes pinning, but ReentrantLock is still more explicit
```

**Flags:**
- `ThreadLocal` in code using Virtual Threads (prefer `ScopedValue`)
- CPU-bound tasks using `Executors.newVirtualThreadPerTaskExecutor()` (use ForkJoinPool instead)
- `synchronized` with blocking operations (prefer `ReentrantLock` for explicit control)
- `spring.threads.virtual.enabled` not enabled in Spring Boot 4

### 5. Collections & Streams

**Check for:**
```java
// ❌ Modifying while iterating
for (Item item : items) {
    if (item.isExpired()) items.remove(item);  // ❌ ConcurrentModificationException
}
// ✅ Correct
items.removeIf(Item::isExpired);

// ❌ Collectors.toList() returns a mutable list — may be surprising
List<String> names = users.stream()
    .map(User::getName)
    .collect(Collectors.toList());  // ❌ mutability not guaranteed

// ✅ Explicit in Java 16+
List<String> names = users.stream()
    .map(User::getName)
    .toList();  // Immutable

// ❌ Avoid complex nested streams; prefer loops for clarity
```

**Flags:**
- `Collectors.toList()` where `.toList()` (Java 16+) is clearer
- Parallel streams without measuring the overhead
- Streams for simple side effects — a plain enhanced for loop is clearer
- Long parameter lists → use DTO/builders

### 6. Classic Concurrency

**Check for:**
```java
// ❌ Not thread-safe
private Map<String, User> cache = new HashMap<>();

// ✅ Thread-safe
private Map<String, User> cache = new ConcurrentHashMap<>();

// ❌ Check-then-act race condition
if (!map.containsKey(key)) {
    map.put(key, computeValue());
}

// ✅ Atomic operation
map.computeIfAbsent(key, k -> computeValue());
```

**Flags:**
- Shared mutable state without synchronization
- Check-then-act patterns without atomicity
- Missing `volatile` on shared variables
- Thread-unsafe lazy initialization
- Static mutable state (prefer dependency injection)

### 7. Java Idioms

**equals/hashCode in Entities:**
```java
// ✅ For JPA entities: use natural key, not auto-incremented ID
@Override
public boolean equals(Object o) {
    if (this == o) return true;
    if (!(o instanceof User user)) return false;
    return isbn != null && isbn.equals(user.isbn);  // Natural key
}

@Override
public int hashCode() {
    return Objects.hash(isbn);  // Consistent with equals
}
```

**Flags:**
- `equals` without `hashCode`
- Mutable fields in `hashCode`
- Missing `toString` on domain objects
- Not using instanceof pattern matching (Java 16+)

### 8. Resource Management

```java
// ❌ Resource leak
FileInputStream fis = new FileInputStream(file);

// ✅ Try-with-resources
try (FileInputStream fis = new FileInputStream(file)) {
    // ...
}
```

**Flags:**
- Not using try-with-resources for `Closeable`/`AutoCloseable`
- Database connections/statements not properly closed

### 9. API Design

```java
// ❌ Boolean parameters — not self-documenting
process(data, true, false);

// ✅ Use enums or named records
process(data, ProcessMode.ASYNC, ErrorHandling.STRICT);

// ✅ Return Optional for absent values
public Optional<User> findById(Long id) {
    return Optional.ofNullable(users.get(id));
}

// ✅ Favor generic bounded types for reusable utilities
public <T extends Identifiable> Map<Long, T> indexById(Collection<T> items) { ... }
```

### 10. Generics and Type Safety

```java
// ❌ Raw types
List list = new ArrayList();
Map map = new HashMap();

// ✅ Typed generics
List<String> list = new ArrayList<>();
Map<String, User> map = new HashMap<>();
```

**Flags:**
- Raw types usage
- Unchecked casts
- Missing generic type parameters in method signatures

### 11. Performance

**Check for:**
```java
// ❌ String concatenation in loop
String result = "";
for (String s : strings) { result += s; }

// ✅ StringBuilder or String.join
String result = String.join("", strings);

// ❌ Regex compilation in loop
for (String line : lines) {
    if (line.matches("pattern.*")) { }
}

// ✅ Pre-compiled pattern
private static final Pattern PATTERN = Pattern.compile("pattern.*");

// ❌ N+1 in loops
for (User user : users) {
    List<Order> orders = orderRepo.findByUserId(user.getId());
}

// ✅ Batch fetch
Map<Long, List<Order>> ordersByUser = orderRepo.findByUserIds(userIds);
```

**Flags:**
- String concatenation in loops
- Regex compilation in loops
- N+1 query patterns
- Not using primitive streams (`IntStream`, `LongStream`) for numeric ops
- Magic numbers → use named constants

### 12. Logging

```java
// ✅ Parameterized logging (no concatenation)
private static final Logger log = LoggerFactory.getLogger(MarketService.class);
log.info("fetch_market slug={}", slug);
log.error("failed_fetch_market slug={}", slug, ex);

// ❌ String concatenation in log statements
log.info("fetch_market slug=" + slug);  // Always evaluated even when level is disabled
```

### 13. Testing Hints

**Suggest tests for:**
- Null inputs / boundary values
- Empty collections
- Exception cases
- Concurrent access (if applicable)
- Uso de `@MockitoBean` (Spring Boot 4) en lugar de `@MockBean` (deprecado)
- JUnit 5 + AssertJ para fluent assertions
- Mockito for mocking; avoid partial mocks where possible
- Favor deterministic tests; no hidden sleeps

---

## Code Smells Reference

| Smell | Problem | Fix |
|-------|---------|-----|
| Long parameter lists | Hard to call, error-prone | Extract DTO/record |
| Deep nesting | Hard to read | Early returns / guard clauses |
| Magic numbers | Cryptic meaning | Named constants |
| Silent catch blocks | Swallows errors | Log and rethrow |
| Broad `catch (Exception)` | Masks real errors | Catch specific types |
| Static mutable state | Thread safety risk | Use DI |
| Boolean parameters | Unclear intent | Use enums |

---

## Severity Guidelines

| Severity | Criteria |
|----------|----------|
| **Critical** | Security vulnerability, data loss risk, production crash |
| **High** | Bug likely, significant performance issue, breaks API contract |
| **Medium** | Code smell, maintainability issue, missing best practice |
| **Low** | Style, minor optimization, suggestion |

## Token Optimization

- Focus on changed lines (use `git diff`)
- Don't repeat obvious issues - group similar findings
- Reference line numbers, not full code quotes
- Skip auto-generated files (OpenAPI, Protobuf)

## Quick Reference Card

| Category | Key Checks |
|----------|------------|
| Standards | PascalCase classes, camelCase fields, UPPER_SNAKE constants |
| Immutability | Records for DTOs, final fields, immutable collections |
| Java 25 | Records, pattern matching, switch expressions, text blocks, var |
| Virtual Threads | ScopedValue > ThreadLocal, no CPU-bound en vThreads |
| Null Safety | Chained calls, Optional misuse, null returns |
| Exceptions | Empty catch, broad catch, lost stack trace |
| Collections | `.toList()` (Java 16+), modification during iteration |
| Concurrency | Shared mutable state, check-then-act |
| Idioms | equals/hashCode pair, toString, builders |
| Resources | try-with-resources, connection leaks |
| API | Boolean params, null handling, validation |
| Performance | String concat, regex in loop, N+1 |
| Logging | Parameterized logging, no concatenation |

---

## Related Skills

- `spring-boot` — Spring Boot 4 with Java 25 Virtual Threads and modern language features
- `clean-ddd-hexagonal` — Java records map to value objects; sealed classes to sum types in the domain layer
- `concurrency-review` — Virtual Threads and structured concurrency are Java 25 concurrency primitives
- `jpa-patterns` — JPA/Hibernate 7 patterns for Java 25 microservices (projections, N+1, transactions)
- `code-simplification` — Java 25 features (pattern matching, records, text blocks) enable significant simplification
