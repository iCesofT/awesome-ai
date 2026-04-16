---
name: observability
description: Observability patterns for Spring Boot 4 microservices using Spring Actuator, Micrometer, OpenTelemetry OTLP, Log4j2 with Disruptor async logging, and liveness/readiness health probes.
metadata:
  version: "1.2.0"
  domain: backend
  triggers: observability, monitoring, metrics, tracing, logging, Actuator, Micrometer, OpenTelemetry, OTLP, Prometheus, Log4j2, health check, liveness, readiness
  role: specialist
  scope: implementation
---

# Observability Skill

Full-stack observability for Spring Boot 4 microservices: metrics (Micrometer/Prometheus), distributed tracing (OpenTelemetry OTLP), high-performance async logging (Log4j2 + Disruptor), and health probes (Actuator).

## When to Use

- Adding metrics, tracing, or structured logging to a Spring Boot microservice
- Configuring Kubernetes liveness and readiness health probes
- Setting up distributed tracing with OpenTelemetry Collector
- Replacing synchronous Logback with high-performance Log4j2 + Disruptor

## Reference Stack

| Component | Purpose |
|-----------|---------|
| Spring Actuator | Health, metrics, info endpoints |
| Micrometer | Metrics abstraction over Prometheus, OTLP, etc. |
| Micrometer Tracing (Brave) | Distributed tracing |
| OTLP Registry | Export to OpenTelemetry Collector |
| gRPC Census | Automatic RPC metrics |
| Log4j2 | High-performance logging |
| LMAX Disruptor | Async queue for Log4j2 (zero-GC) |

---

## Spring Actuator: Health Probes

### application.yaml

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics,prometheus
      base-path: /actuator
  endpoint:
    health:
      show-details: always
      probes:
        enabled: true   # Enables /actuator/health/liveness and /actuator/health/readiness
  health:
    livenessstate:
      enabled: true    # App alive (keep running) vs dead (Kubernetes restart)
    readinessstate:
      enabled: true    # App ready (accept traffic) vs not ready (remove from load balancer)
```

### Available Endpoints

| Endpoint | Purpose |
|---------|---------|
| `/actuator/health` | Overall status (liveness + readiness + dependencies) |
| `/actuator/health/liveness` | Kubernetes liveness probe |
| `/actuator/health/readiness` | Kubernetes readiness probe |
| `/actuator/metrics` | List of available metrics |
| `/actuator/metrics/{name}` | Value of a specific metric |
| `/actuator/prometheus` | Prometheus scrape endpoint |
| `/actuator/info` | Build info (git commit, version) |

### Security: Permitir health sin auth

```java
@Configuration
@EnableMethodSecurity
public class SecurityConfig {
    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        return http
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/actuator/health/**").permitAll()
                .requestMatchers("/actuator/prometheus").hasRole("MONITORING")
                .anyRequest().authenticated())
            .build();
    }
}
```

### Custom Health Indicator

```java
@Component
public class ExternalServiceHealthIndicator implements HealthIndicator {

    private final ExternalServiceClient client;

    @Override
    public Health health() {
        try {
            boolean available = client.ping();
            return available
                ? Health.up().withDetail("service", "ExternalService").build()
                : Health.down().withDetail("error", "Service not responding").build();
        } catch (Exception e) {
            return Health.down()
                .withDetail("error", e.getMessage())
                .withException(e)
                .build();
        }
    }
}
```

---

## Micrometer: Business Metrics

### Maven Dependencies

```xml
<!-- Bootstrap module pom.xml -->
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-registry-prometheus</artifactId>
</dependency>
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-tracing-bridge-brave</artifactId>
</dependency>
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-registry-otlp</artifactId>
</dependency>
```

### Counters and Timers

```java
@Service
public class ProductCommandService {

    private final MeterRegistry meterRegistry;
    private final Counter productsCreatedCounter;
    private final Timer productCreationTimer;

    public ProductCommandService(MeterRegistry meterRegistry) {
        this.meterRegistry = meterRegistry;
        this.productsCreatedCounter = Counter.builder("products.created")
            .description("Total products created")
            .tag("service", "catalog")
            .register(meterRegistry);
        this.productCreationTimer = Timer.builder("products.creation.duration")
            .description("Time to create a product")
            .register(meterRegistry);
    }

    public Product create(CreateProductCommand command) {
        return productCreationTimer.record(() -> {
            Product product = new Product(command.name(), command.price());
            Product saved = productRepository.save(product);
            productsCreatedCounter.increment();
            return saved;
        });
    }
}
```

### @Timed: Declarative Timing

```java
@Component
@Timed(value = "catalog.service", extraTags = {"layer", "application"})
public class ProductQueryService {

    @Timed(value = "catalog.products.findById", description = "Find product by ID")
    public Optional<Product> findById(Long id) {
        return productRepository.findById(new ProductId(id));
    }
}
```

### Gauge for State Monitoring

```java
@Configuration
public class MetricsConfig {

    @Bean
    public MeterBinder activeConnectionsGauge(DataSource dataSource) {
        return registry -> Gauge.builder("db.pool.active_connections",
                dataSource,
                ds -> {
                    try {
                        return ((HikariDataSource) ds).getHikariPoolMXBean()
                            .getActiveConnections();
                    } catch (Exception e) {
                        return 0;
                    }
                })
            .description("HikariCP active connections")
            .register(registry);
    }
}
```

---

## OpenTelemetry OTLP: Distributed Tracing

### OTLP Configuration

```yaml
management:
  otlp:
    tracing:
      endpoint: ${OTLP_ENDPOINT:http://otel-collector:4318/v1/traces}
  tracing:
    sampling:
      probability: ${TRACING_SAMPLING_PROBABILITY:1.0}  # 1.0 in dev; reduce in prod for high-traffic services
```

### Manual Tracing with @Observed

```java
@Service
@Observed(name = "product.service")  // Auto-creates a span
public class ProductQueryService {

    private final Tracer tracer;

    // Constructor injection

    public List<Product> findByStatus(String status) {
        // Manual tracing for additional context
        Span span = tracer.nextSpan().name("product.query.byStatus");
        try (Tracer.SpanInScope ignored = tracer.withSpan(span.start())) {
            span.tag("filter.status", status);
            return productRepository.findByStatus(ProductStatus.valueOf(status));
        } catch (Exception e) {
            span.error(e);
            throw e;
        } finally {
            span.end();
        }
    }
}
```

### Automatic Context Propagation in Spring Boot 4

Spring Boot 4 propagates trace context automatically across:
- HTTP requests (REST controllers)
- `@Async` methods
- Virtual Threads
- gRPC (with grpc-census)

---

## Log4j2 + Disruptor: Async Logging

### Maven: Exclude Logback, Add Log4j2

```xml
<!-- Root pom.xml — exclude Spring Boot's default logging starter -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter</artifactId>
    <exclusions>
        <exclusion>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-logging</artifactId>
        </exclusion>
    </exclusions>
</dependency>

<!-- Bootstrap module pom.xml -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-log4j2</artifactId>
</dependency>
<!-- Disruptor: high-throughput queue for async logging (zero-GC) -->
<dependency>
    <groupId>com.lmax</groupId>
    <artifactId>disruptor</artifactId>
    <version>${disruptor.version}</version>  <!-- 4.0.0 -->
</dependency>
<!-- SLF4J bridge for libraries that use Commons Logging -->
<dependency>
    <groupId>org.slf4j</groupId>
    <artifactId>jcl-over-slf4j</artifactId>
</dependency>
```

### log4j2.xml (Bootstrap module resources)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Configuration status="WARN" monitorInterval="30">

    <Properties>
        <Property name="LOG_PATTERN">
            %d{yyyy-MM-dd HH:mm:ss.SSS} [%t] %-5level [%X{traceId},%X{spanId}] %logger{36} - %msg%n
        </Property>
    </Properties>

    <Appenders>
        <!-- Console appender: for development and containers -->
        <Console name="Console" target="SYSTEM_OUT">
            <PatternLayout pattern="${LOG_PATTERN}"/>
        </Console>

        <!-- Async appender with Disruptor: high throughput, non-blocking -->
        <Async name="AsyncConsole" includeLocation="false" bufferSize="262144">
            <AppenderRef ref="Console"/>
        </Async>
    </Appenders>

    <Loggers>
        <!-- Application-specific loggers -->
        <Logger name="io.github.example.catalog" level="INFO" additivity="false">
            <AppenderRef ref="AsyncConsole"/>
        </Logger>
        <Logger name="org.springframework.web" level="INFO" additivity="false">
            <AppenderRef ref="AsyncConsole"/>
        </Logger>
        <Logger name="org.hibernate.SQL" level="${env:DATASOURCE_LOG_LEVEL:-WARN}" additivity="false">
            <AppenderRef ref="AsyncConsole"/>
        </Logger>
        <Logger name="com.zaxxer.hikari" level="INFO" additivity="false">
            <AppenderRef ref="AsyncConsole"/>
        </Logger>

        <!-- Root logger (catch-all) -->
        <Root level="WARN">
            <AppenderRef ref="AsyncConsole"/>
        </Root>
    </Loggers>

</Configuration>
```

### Structured Logging with MDC (trace correlation)

```java
// Spring Boot + Micrometer automatically propagates traceId/spanId into MDC
// Include them in the Log4j2 pattern: %X{traceId},%X{spanId}

// Manual logging with additional context
@Component
public class ProductService {
    private static final Logger log = LogManager.getLogger(ProductService.class);

    public Product findById(Long id) {
        // ✅ Parameterized logging (no string concatenation)
        log.debug("Looking up product with id={}", id);

        return productRepository.findById(id)
            .orElseThrow(() -> {
                log.warn("Product not found id={}", id);
                return new EntityNotFoundException("Product not found: " + id);
            });
    }
}
```

---

## Build Info en /actuator/info

```xml
<!-- Spring Boot Maven Plugin with git-commit-id -->
<plugin>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-maven-plugin</artifactId>
</plugin>
<plugin>
    <groupId>pl.project13.maven</groupId>
    <artifactId>git-commit-id-plugin</artifactId>
    <version>${git-commit-id-maven-plugin.version}</version>
</plugin>
```

```yaml
management:
  info:
    git:
      mode: full      # Includes branch, commit, build time in /actuator/info
    build:
      enabled: true
```

---

## Observability Checklist

### Health
- [ ] `/actuator/health` responds UP
- [ ] `/actuator/health/liveness` and `/readiness` probes enabled
- [ ] Dependency health checks: DB, Redis, external services
- [ ] Kubernetes probes configured (liveness more permissive than readiness)

### Metrics
- [ ] `/actuator/prometheus` scrape endpoint accessible
- [ ] Business metrics with `Counter`/`Timer`/`Gauge`
- [ ] JVM metrics active (heap, GC, threads)
- [ ] DB metrics: HikariCP pool, query timings
- [ ] Cache metrics: hit/miss rate

### Tracing
- [ ] OTLP endpoint configured
- [ ] `traceId` present in logs (Log4j2 pattern includes `%X{traceId}`)
- [ ] Sampling rate tuned (not 100% in production under high traffic)

### Logging
- [ ] Log4j2 + Disruptor async (not synchronous Logback)
- [ ] Parameterized logging (no string concatenation `"msg" + var`)
- [ ] No sensitive data in logs (passwords, tokens, PII)
- [ ] Correct log levels: DEBUG in dev, INFO/WARN in prod
- [ ] Log level externalized via env var: `${env:LOG_LEVEL:-INFO}`

---

## Graceful Shutdown con Actuator

```yaml
server:
  shutdown: graceful    # Spring Boot completes in-flight requests before stopping

spring:
  lifecycle:
    timeout-per-shutdown-phase: ${SHUTDOWN_TIMEOUT:30s}
```

With this configuration and `exec java $JAVA_OPTS org.springframework.boot.loader.launch.JarLauncher` in the Dockerfile (SIGTERM → JVM → Spring graceful shutdown), the Kubernetes pod shuts down cleanly.

---

## Related Skills

- `spring-boot` — Base application setup, Actuator and Virtual Threads configuration
- `logging-patterns` — Structured logging conventions, MDC, and log levels in production
- `deployment-patterns` — Blue/green deployments, Kubernetes probes, and container lifecycle
- `springboot-security` — Securing Actuator endpoints, Prometheus scrape authorization
- `multi-stage-dockerfile` — Building minimal container images that export SIGTERM correctly
