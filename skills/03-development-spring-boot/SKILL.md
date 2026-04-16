---
name: spring-boot
description: Spring Boot 4.x development - REST APIs, JPA, Security, Testing, and Cloud-native patterns with Java 25, Virtual Threads, and hexagonal architecture. Use for building enterprise Java microservices.
metadata:
  version: "1.2.0"
  domain: backend
  triggers: Spring Boot, Spring Boot 4, Spring Framework, Spring Security, Spring Data JPA, Spring WebFlux, Java REST API, Microservices Java, Java 25
  role: specialist
  scope: implementation
  output-format: code
---

# Spring Boot Skill

Enterprise Spring Boot 4.x development with Java 25, Virtual Threads, and hexagonal architecture patterns.

## When to Use

- Building new REST or gRPC microservices with Spring Boot
- Implementing hexagonal or clean architecture in a Java service
- Configuring JPA, Liquibase, Redis, or Spring Security in a Spring Boot application
- Migrating from Spring Boot 2.x/3.x patterns to Spring Boot 4.x
- Setting up multi-module Maven projects for a new service

## Reference Stack

| Component | Version |
|-----------|---------|
| Java | 25 |
| Spring Boot | 4.0.x |
| Spring Cloud | 2025.1.x |
| Spring Data | 2025.1.x |
| Spring gRPC | 1.0.x |
| Hibernate | 7.3.x |
| Liquibase | 5.0.x |

## Core Workflow

1. **Analyze** - Understand requirements, identify service boundaries, APIs, data models
2. **Design** - Plan architecture (hexagonal recommended), confirm before coding
3. **Implement** - Build with constructor injection, records for DTOs, virtual threads
4. **Secure** - Add Spring Security 6, OAuth2, method security
5. **Test** - Unit, integration (Testcontainers), BDD (Cucumber)
6. **Deploy** - Configure health probes via Actuator; validate liveness/readiness

## Recommended Multi-module Structure

```
my-service/
├── pom.xml                          ← BOM + plugin management
├── my-domain/                       ← No external dependencies
├── my-application/                  ← Depends on domain only
├── my-infrastructure/
│   ├── pom.xml
│   ├── my-infrastructure-api-rest/  ← OpenAPI-generated controllers
│   ├── my-infrastructure-api-grpc/  ← Protobuf-generated services
│   ├── my-infrastructure-api-common/
│   └── my-infrastructure-persistence-jpa/  ← JPA + Liquibase + Redis
└── my-bootstrap/                    ← Spring Boot entry point
```

---

## Virtual Threads (Java 25 + Spring Boot 4)

Spring Boot 4 enables Virtual Threads with a single property:

```yaml
spring:
  threads:
    virtual:
      enabled: true  # Enables Loom for Tomcat, @Async, @Scheduled, etc.
```

```java
// With Virtual Threads enabled, I/O ExecutorService instances use Loom:
try (ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor()) {
    List<Future<Result>> futures = requests.stream()
        .map(req -> executor.submit(() -> callExternalApi(req)))
        .toList();
}
```

---

## Quick Start Templates

### Entity (Hexagonal - Pure Domain)

```java
// In catalog-domain - no framework dependencies
public class Product {
    private final ProductId id;
    private String name;
    private Money price;

    public Product(ProductId id, String name, Money price) {
        this.id = Objects.requireNonNull(id);
        this.name = Objects.requireNonNull(name);
        this.price = Objects.requireNonNull(price);
    }
    // Getters, domain methods
}
```

### Repository Port (Domain)

```java
// Port in domain - pure interface
public interface ProductRepository {
    Optional<Product> findById(ProductId id);
    List<Product> findByName(String name);
    Product save(Product product);
}
```

### JPA Entity (Infrastructure)

```java
@Entity
@Table(name = "products")
public class ProductJpaEntity {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @NotBlank
    private String name;

    @DecimalMin("0.0")
    private BigDecimal price;
}
```

### JPA Repository Adapter

```java
@Repository
public class ProductRepositoryAdapter implements ProductRepository {
    private final ProductJpaRepository jpaRepo;
    private final ProductMapper mapper;

    public ProductRepositoryAdapter(ProductJpaRepository jpaRepo, ProductMapper mapper) {
        this.jpaRepo = jpaRepo;
        this.mapper = mapper;
    }

    @Override
    public Optional<Product> findById(ProductId id) {
        return jpaRepo.findById(id.value()).map(mapper::toDomain);
    }
}
```

### Application Service (Use Case)

```java
@Service
@Transactional(readOnly = true)
public class ProductQueryService {
    private final ProductRepository productRepository;

    public ProductQueryService(ProductRepository productRepository) {
        this.productRepository = productRepository;
    }

    public List<Product> search(String name) {
        return productRepository.findByName(name);
    }

    @Transactional
    public Product create(CreateProductCommand command) {
        var product = new Product(ProductId.generate(), command.name(), command.price());
        return productRepository.save(product);
    }
}
```

### REST Controller (OpenAPI Delegate Pattern)

```java
// Controller implements the interface generated by openapi-generator
@RestController
public class ProductApiController implements ProductsApi {
    private final ProductApiDelegate delegate;

    public ProductApiController(ProductApiDelegate delegate) {
        this.delegate = delegate;
    }

    @Override
    public ResponseEntity<List<ProductDto>> listProducts() {
        return delegate.listProducts();
    }
}

// Delegate implements the actual logic
@Component
public class ProductApiDelegateImpl implements ProductApiDelegate {
    private final ProductQueryService queryService;
    private final ProductMapper mapper;

    @Override
    public ResponseEntity<List<ProductDto>> listProducts() {
        return ResponseEntity.ok(
            queryService.search("").stream()
                .map(mapper::toDto)
                .toList()
        );
    }
}
```

### REST Controller (Direct style with @Validated)

```java
@RestController
@RequestMapping("/api/markets")
@Validated
class MarketController {
    private final MarketService marketService;

    MarketController(MarketService marketService) {
        this.marketService = marketService;
    }

    @GetMapping
    ResponseEntity<Page<MarketResponse>> list(
        @RequestParam(defaultValue = "0") int page,
        @RequestParam(defaultValue = "20") int size) {
        Page<Market> markets = marketService.list(PageRequest.of(page, size));
        return ResponseEntity.ok(markets.map(MarketResponse::from));
    }

    @PostMapping
    ResponseEntity<MarketResponse> create(@Valid @RequestBody CreateMarketRequest request) {
        Market market = marketService.create(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(MarketResponse.from(market));
    }
}
```

### DTO with Record

```java
public record CreateProductCommand(
    @NotBlank String name,
    @DecimalMin("0.0") BigDecimal price
) {}

public record CreateMarketRequest(
    @NotBlank @Size(max = 200) String name,
    @NotBlank @Size(max = 2000) String description,
    @NotNull @FutureOrPresent Instant endDate,
    @NotEmpty List<@NotBlank String> categories) {}

public record MarketResponse(Long id, String name, MarketStatus status) {
    static MarketResponse from(Market market) {
        return new MarketResponse(market.id(), market.name(), market.status());
    }
}
```

### Global Exception Handler (ProblemDetail - RFC 9457)

```java
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(MethodArgumentNotValidException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public ProblemDetail handleValidation(MethodArgumentNotValidException ex) {
        var problem = ProblemDetail.forStatus(HttpStatus.BAD_REQUEST);
        problem.setTitle("Validation Error");
        problem.setProperty("errors", ex.getBindingResult().getFieldErrors().stream()
            .collect(Collectors.toMap(FieldError::getField,
                e -> e.getDefaultMessage() != null ? e.getDefaultMessage() : "Invalid")));
        return problem;
    }

    @ExceptionHandler(EntityNotFoundException.class)
    @ResponseStatus(HttpStatus.NOT_FOUND)
    public ProblemDetail handleNotFound(EntityNotFoundException ex) {
        var problem = ProblemDetail.forStatus(HttpStatus.NOT_FOUND);
        problem.setDetail(ex.getMessage());
        return problem;
    }

    @ExceptionHandler(AccessDeniedException.class)
    @ResponseStatus(HttpStatus.FORBIDDEN)
    public ProblemDetail handleAccessDenied(AccessDeniedException ex) {
        return ProblemDetail.forStatusAndDetail(HttpStatus.FORBIDDEN, "Access denied");
    }

    @ExceptionHandler(Exception.class)
    @ResponseStatus(HttpStatus.INTERNAL_SERVER_ERROR)
    public ProblemDetail handleGeneric(Exception ex) {
        // Log with stack trace for unexpected errors
        return ProblemDetail.forStatusAndDetail(HttpStatus.INTERNAL_SERVER_ERROR,
            "Internal server error");
    }
}
```

### Test Slice

```java
@WebMvcTest(ProductApiController.class)
class ProductApiControllerTest {
    @Autowired MockMvc mockMvc;
    @MockitoBean ProductApiDelegate delegate;  // Spring Boot 4 uses @MockitoBean

    @Test
    void listProducts_returnsOk() throws Exception {
        when(delegate.listProducts()).thenReturn(ResponseEntity.ok(List.of()));

        mockMvc.perform(get("/api/v1/products"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray());
    }
}
```

---

## Middleware / Filters

### Request Logging Filter

```java
@Component
public class RequestLoggingFilter extends OncePerRequestFilter {
    private static final Logger log = LoggerFactory.getLogger(RequestLoggingFilter.class);

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
        FilterChain filterChain) throws ServletException, IOException {
        long start = System.currentTimeMillis();
        try {
            filterChain.doFilter(request, response);
        } finally {
            long duration = System.currentTimeMillis() - start;
            log.info("req method={} uri={} status={} durationMs={}",
                request.getMethod(), request.getRequestURI(), response.getStatus(), duration);
        }
    }
}
```

### Rate Limiting Filter (Bucket4j)

**Security Note**: `X-Forwarded-For` header is untrusted by default — clients can spoof it. Only use forwarded headers when behind a trusted reverse proxy with `ForwardedHeaderFilter` properly configured.

```java
@Component
public class RateLimitFilter extends OncePerRequestFilter {
    private final Map<String, Bucket> buckets = new ConcurrentHashMap<>();

    /*
     * SECURITY: Uses request.getRemoteAddr() for client IP.
     * Behind a proxy, configure: server.forward-headers-strategy=NATIVE (or FRAMEWORK)
     * and register ForwardedHeaderFilter. Never read X-Forwarded-For directly.
     */
    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
        FilterChain filterChain) throws ServletException, IOException {
        String clientIp = request.getRemoteAddr();

        Bucket bucket = buckets.computeIfAbsent(clientIp,
            k -> Bucket.builder()
                .addLimit(Bandwidth.classic(100, Refill.greedy(100, Duration.ofMinutes(1))))
                .build());

        if (bucket.tryConsume(1)) {
            filterChain.doFilter(request, response);
        } else {
            response.setStatus(HttpStatus.TOO_MANY_REQUESTS.value());
        }
    }
}
```

---

## Async Processing

```java
@Service
public class NotificationService {
    @Async  // Requires @EnableAsync on a @Configuration class
    public CompletableFuture<Void> sendAsync(Notification notification) {
        // send email/SMS
        return CompletableFuture.completedFuture(null);
    }
}
```

---

## Error-Resilient External Calls

```java
public <T> T withRetry(Supplier<T> supplier, int maxRetries) {
    int attempts = 0;
    while (true) {
        try {
            return supplier.get();
        } catch (Exception ex) {
            attempts++;
            if (attempts >= maxRetries) throw ex;
            try {
                Thread.sleep((long) Math.pow(2, attempts) * 100L);
            } catch (InterruptedException ie) {
                Thread.currentThread().interrupt();
                throw ex;
            }
        }
    }
}
```

---

## Reference application.yaml

```yaml
server:
  port: ${SERVER_PORT:8080}
  http2.enabled: true
  compression:
    enabled: true
    mime-types: [application/json, application/xml]
  shutdown: graceful
  servlet:
    context-path: /api/v1
  tomcat:
    threads:
      max: ${TOMCAT_MAX_THREADS:400}

management:
  endpoints:
    web.exposure.include: health,info,metrics,prometheus
  endpoint:
    health:
      show-details: always
      probes:
        enabled: true
  health:
    livenessstate.enabled: true
    readinessstate.enabled: true

spring:
  application.name: '@project.artifactId@'
  threads:
    virtual:
      enabled: ${VIRTUAL_THREADS_ENABLED:true}
  datasource:
    url: ${DATABASE_URL:jdbc:postgresql://localhost:5432/mydb}
    username: ${DATABASE_USERNAME:user}
    password: ${DATABASE_PASSWORD:pass}
    hikari:
      maximum-pool-size: ${DATASOURCE_MAXIMUM_POOL_SIZE:50}
      minimum-idle: ${DATASOURCE_MINIMUM_IDLE:10}
      connection-timeout: ${DATABASE_CONNECTION_TIMEOUT:5000}
  jpa:
    hibernate:
      ddl-auto: validate
    show-sql: ${DATASOURCE_SHOW_SQL:false}
    properties:
      hibernate:
        dialect: org.hibernate.dialect.PostgreSQLDialect
        jdbc.batch_size: 25
  cache.type: redis
  data.redis:
    host: ${REDIS_HOST:localhost}
    port: ${REDIS_PORT:6379}
  grpc:
    server:
      port: ${GRPC_SERVER_PORT:9090}
      reflection.enabled: true
  mvc:
    problemdetails:
      enabled: true  # RFC 9457 ProblemDetail responses
```

---

## pom.xml Root (BOM Pattern)

```xml
<properties>
    <java.version>25</java.version>
    <spring-boot.version>4.0.5</spring-boot.version>
    <spring-cloud.version>2025.1.1</spring-cloud.version>
    <spring-data.version>2025.1.4</spring-data.version>
    <hibernate.version>7.3.0.Final</hibernate.version>
    <liquibase-maven-plugin.version>5.0.2</liquibase-maven-plugin.version>
    <openapi-generator-maven-plugin.version>7.21.0</openapi-generator-maven-plugin.version>
    <mapstruct.version>1.6.3</mapstruct.version>
    <lombok.version>1.18.44</lombok.version>
</properties>

<!-- Compiler with annotation processors for Lombok + MapStruct + Hibernate Metamodel -->
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-compiler-plugin</artifactId>
    <version>3.15.0</version>
    <configuration>
        <release>${java.version}</release>
        <annotationProcessorPaths>
            <path>
                <groupId>org.projectlombok</groupId>
                <artifactId>lombok</artifactId>
                <version>${lombok.version}</version>
            </path>
            <path>
                <groupId>org.mapstruct</groupId>
                <artifactId>mapstruct-processor</artifactId>
                <version>${mapstruct.version}</version>
            </path>
            <path>
                <groupId>org.hibernate.orm</groupId>
                <artifactId>hibernate-jpamodelgen</artifactId>
                <version>${hibernate.version}</version>
            </path>
            <path>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-configuration-processor</artifactId>
            </path>
        </annotationProcessorPaths>
    </configuration>
</plugin>
```

---

## Spring Security JWT (Spring Boot 4)

```java
@Configuration
@EnableMethodSecurity
public class SecurityConfig {
    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        return http
            .csrf(AbstractHttpConfigurer::disable)
            .sessionManagement(s -> s.sessionCreationPolicy(STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/actuator/health/**").permitAll()
                .anyRequest().authenticated())
            .oauth2ResourceServer(oauth2 -> oauth2.jwt(Customizer.withDefaults()))
            .build();
    }
}
```

---

## Constraints

### MUST DO
- Constructor injection (no field injection)
- `@Valid` on request bodies
- `@Transactional` for multi-step writes
- `@Transactional(readOnly = true)` for reads
- `@ConfigurationProperties` for typed configuration
- `@RestControllerAdvice` + `ProblemDetail` (RFC 9457) for error responses
- Virtual Threads enabled (`spring.threads.virtual.enabled=true`)
- `ddl-auto: validate` in production (Liquibase manages the schema)
- Records for immutable DTOs/Commands/Queries

### MUST NOT DO
- Field injection (`@Autowired` on fields)
- Skip input validation at endpoints
- Mix blocking and reactive code
- Store secrets in `application.properties`
- Use patterns deprecated in Spring Boot 2.x/3.x
- `@MockBean` (deprecated) — use `@MockitoBean` in Spring Boot 4
- `ddl-auto: create/update` in production
- Read `X-Forwarded-For` directly without `ForwardedHeaderFilter` configured

---

## Knowledge Base

Java 25, Spring Boot 4.x, Virtual Threads (Project Loom), Spring gRPC, Spring Data 2025, Hibernate 7, JPA/Jakarta EE 11, PostgreSQL, Liquibase 5, Redis, Caffeine, OpenAPI 3.0 (design-first), Protobuf/gRPC, Cucumber 7, Testcontainers, Log4j2+Disruptor, Micrometer/OTLP, MapStruct, Lombok, Maven multi-module, Docker/Alpine

## Related Skills

- `jpa-patterns` — JPA entity design, N+1 prevention, query optimization
- `liquibase` — Database schema migration with Liquibase 5 and DDL/DML separation
- `spring-boot-testing` — `@WebMvcTest`, `@DataJpaTest`, Testcontainers integration tests
- `bdd-patterns` — Cucumber 7 BDD acceptance tests in the application layer
- `springboot-security` — Spring Security 6, JWT, OAuth2, and method-level authorization
- `grpc-design` — gRPC service design with Protobuf and Spring gRPC
- `clean-ddd-hexagonal` — Hexagonal architecture, ports & adapters, domain layer design
