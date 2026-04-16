---
name: caching-patterns
description: Caching patterns with Spring Cache abstraction, Redis (distributed) and Caffeine (local/L1) for Spring Boot 4 microservices. Covers configuration, annotations, eviction, TTL, and two-level cache strategies.
metadata:
  version: "1.2.0"
  domain: backend
  triggers: cache, Redis, Caffeine, Spring Cache, @Cacheable, @CacheEvict, distributed cache, in-memory cache, performance
  role: specialist
  scope: implementation
---

# Caching Patterns Skill

Caching strategies with Spring Cache, Redis, and Caffeine in Spring Boot 4 microservices.

## When to Use
- Low-volatility reference data (catalogs, enumerations)
- Frequent queries with stable results
- Reducing database load
- High read latency on frequently accessed operations

## Reference Stack

| Component | Version |
|-----------|---------|
| Spring Boot Starter Cache | 4.0.x |
| Spring Data Redis | 4.0.x |
| Lettuce (Redis client) | 6.x |
| Caffeine | 3.2.3 |
| Redis | 7.x / 8.x |

---

## Spring Boot Configuration

### application.yaml — Redis as primary cache

```yaml
spring:
  cache:
    type: redis   # Spring Boot will use Redis as the default CacheManager
  data:
    redis:
      host: ${REDIS_HOST:localhost}
      port: ${REDIS_PORT:6379}
      lettuce:
        pool:
          max-active: ${REDIS_MAX_ACTIVE:50}
          max-idle: ${REDIS_MAX_IDLE:10}
          min-idle: ${REDIS_MIN_IDLE:10}
          max-wait: ${REDIS_MAX_WAIT:5000}  # ms
```

### @EnableCaching

```java
@Configuration
@EnableCaching
public class CacheConfig {

    // Redis Cache Manager bean with TTL and JSON serialization
    @Bean
    public RedisCacheManagerBuilderCustomizer redisCacheManagerBuilderCustomizer() {
        return builder -> builder
            .withCacheConfiguration("products",
                RedisCacheConfiguration.defaultCacheConfig()
                    .entryTtl(Duration.ofMinutes(30))
                    .serializeValuesWith(
                        RedisSerializationContext.SerializationPair.fromSerializer(
                            new GenericJackson2JsonRedisSerializer()
                        )
                    )
            )
            .withCacheConfiguration("categories",
                RedisCacheConfiguration.defaultCacheConfig()
                    .entryTtl(Duration.ofHours(24))  // More stable data
            )
            .withCacheConfiguration("provinces",
                RedisCacheConfiguration.defaultCacheConfig()
                    .entryTtl(Duration.ofDays(7))    // Static geographic data
            );
    }
}
```

---

## Spring Cache Annotations

### @Cacheable — Store Result

```java
@Service
@Transactional(readOnly = true)
public class ProductQueryService {

    // ✅ Cache query result
    @Cacheable(value = "products", key = "#id")
    public Optional<Product> findById(Long id) {
        return productRepository.findById(new ProductId(id));
    }

    // ✅ Cache entire list
    @Cacheable(value = "products", key = "'all-active'")
    public List<Product> findAllActive() {
        return productRepository.findByStatus(ProductStatus.ACTIVE);
    }

    // ✅ Conditional cache (only cache if result is non-empty)
    @Cacheable(value = "products", key = "#status", condition = "#status != null",
               unless = "#result.isEmpty()")
    public List<Product> findByStatus(String status) {
        return productRepository.findByStatus(ProductStatus.valueOf(status));
    }
}
```

### @CacheEvict — Invalidate Cache

```java
@Service
public class ProductCommandService {

    // ✅ Evict specific entry on update
    @CacheEvict(value = "products", key = "#product.id.value")
    @Transactional
    public Product update(Product product) {
        return productRepository.save(product);
    }

    // ✅ Clear entire cache on delete
    @CacheEvict(value = "products", allEntries = true)
    @Transactional
    public void delete(Long id) {
        productRepository.deleteById(new ProductId(id));
    }
}
```

### @CachePut — Update Cache Without Skipping

```java
// ✅ Always executes the method AND updates the cache
// (unlike @Cacheable which may return directly from cache)
@CachePut(value = "products", key = "#result.id.value")
@Transactional
public Product create(CreateProductCommand command) {
    var product = new Product(command.name(), command.price());
    return productRepository.save(product);
}
```

### @Caching — Multiple Operations

```java
// ✅ Combine multiple cache annotations
@Caching(evict = {
    @CacheEvict(value = "products", key = "#id"),
    @CacheEvict(value = "products", key = "'all-active'"),
    @CacheEvict(value = "categories", allEntries = true)
})
@Transactional
public void deleteProduct(Long id) {
    productRepository.deleteById(new ProductId(id));
}
```

---

## Caffeine: Local Cache (L1)

Caffeine is an in-process Java cache, ideal as an L1 layer before Redis.

### Caffeine Configuration

```yaml
spring:
  cache:
    type: caffeine
    caffeine:
      spec: maximumSize=500,expireAfterWrite=10m
```

### Programmatic Configuration

```java
@Configuration
@EnableCaching
public class CaffeineConfig {

    @Bean
    public CacheManager cacheManager() {
        CaffeineCacheManager cacheManager = new CaffeineCacheManager();
        cacheManager.setCaffeine(Caffeine.newBuilder()
            .maximumSize(1000)                     // Maximum 1000 entries
            .expireAfterWrite(10, TimeUnit.MINUTES) // TTL from write
            .expireAfterAccess(5, TimeUnit.MINUTES) // TTL from last access
            .recordStats()                          // Enable hit/miss statistics
        );
        return cacheManager;
    }
}
```

---

## Two-Level Cache Strategy (L1 Caffeine + L2 Redis)

For high-read-frequency microservices: Caffeine as L1 (local, sub-millisecond) and Redis as L2 (distributed, shared across instances).

```java
@Configuration
@EnableCaching
public class TwoLevelCacheConfig {

    @Bean
    @Primary
    public CacheManager cacheManager(RedisConnectionFactory redisFactory) {
        // L1: Caffeine (local, sub-millisecond)
        Cache l1Cache = Caffeine.newBuilder()
            .maximumSize(500)
            .expireAfterWrite(2, TimeUnit.MINUTES)
            .build();

        // L2: Redis (distributed, shared across pods)
        RedisCacheManager l2Cache = RedisCacheManager.builder(redisFactory)
            .cacheDefaults(RedisCacheConfiguration.defaultCacheConfig()
                .entryTtl(Duration.ofMinutes(30)))
            .build();

        // CompositeCacheManager: looks up in L1 first, then L2
        return new CompositeCacheManager(
            new CaffeineCacheManager("products", "categories"),
            l2Cache
        );
    }
}
```

---

## Redis Cache Manager Avanzado

```java
@Configuration
@EnableCaching
public class RedisCacheConfig {

    private static final ObjectMapper objectMapper = new ObjectMapper()
        .findAndRegisterModules()
        .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);

    @Bean
    public RedisCacheManager redisCacheManager(RedisConnectionFactory factory) {
        RedisCacheConfiguration defaultConfig = RedisCacheConfiguration
            .defaultCacheConfig()
            .entryTtl(Duration.ofMinutes(30))
            .disableCachingNullValues()
            .serializeKeysWith(
                RedisSerializationContext.SerializationPair.fromSerializer(new StringRedisSerializer())
            )
            .serializeValuesWith(
                RedisSerializationContext.SerializationPair.fromSerializer(
                    new GenericJackson2JsonRedisSerializer(objectMapper)
                )
            );

        return RedisCacheManager.builder(factory)
            .cacheDefaults(defaultConfig)
            // Cache-specific TTL overrides
            .withCacheConfiguration("products",
                defaultConfig.entryTtl(Duration.ofMinutes(30)))
            .withCacheConfiguration("provinces",
                defaultConfig.entryTtl(Duration.ofDays(7)))  // Static geographic data
            .withCacheConfiguration("categories",
                defaultConfig.entryTtl(Duration.ofHours(24)))
            .build();
    }
}
```

---

## Redis Connection Pool (Lettuce)

```yaml
spring:
  data:
    redis:
      host: ${REDIS_HOST:localhost}
      port: ${REDIS_PORT:6379}
      lettuce:
        pool:
          max-active: ${REDIS_MAX_ACTIVE:50}   # Max active connections
          max-idle: ${REDIS_MAX_IDLE:10}        # Max idle connections
          min-idle: ${REDIS_MIN_IDLE:10}        # Min idle connections (warm pool)
          max-wait: ${REDIS_MAX_WAIT:5000}      # Connection acquisition timeout (ms)
```

---

## DTO Serialization for Redis

Objects cached in Redis must be serializable. Use simple DTOs (not JPA entities):

```java
// ✅ Serializable DTO for Redis cache
public record ProductCacheDto(
    Long id,
    String name,
    BigDecimal price,
    String status
) implements Serializable {}  // O solo Jackson annotations (sin implements Serializable)

// Mapper
@Mapper(componentModel = "spring")
public interface ProductCacheMapper {
    ProductCacheDto toCacheDto(Product product);
    Product fromCacheDto(ProductCacheDto dto);
}
```

---

## docker-compose Redis

```yaml
redis:
  image: redis:8.0-alpine
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 3s
    retries: 5
  command: redis-server
    --maxmemory 256mb
    --maxmemory-policy allkeys-lru   # Evict least recently used entries
    --save ""                        # Disable RDB persistence (pure cache mode)
    --appendonly no                  # Disable AOF persistence
```

---

## Observabilidad: Cache Hit/Miss

With Spring Actuator and Micrometer, cache metrics are exposed automatically:

```
cache.gets{cache="products",cacheManager="cacheManager",result="hit"}
cache.gets{cache="products",cacheManager="cacheManager",result="miss"}
cache.puts{cache="products"}
cache.evictions{cache="products"}
```

Con Caffeine `recordStats()` activo:

```java
@Component
public class CacheMetricsLogger {

    @Autowired
    private CacheManager cacheManager;

    @Scheduled(fixedDelay = 60_000)
    public void logStats() {
        if (cacheManager instanceof CaffeineCacheManager ccm) {
            ccm.getCacheNames().forEach(name -> {
                var cache = ccm.getCache(name);
                // Log hit rate, miss rate, eviction count
            });
        }
    }
}
```

---

## Cache Tests

```java
@SpringBootTest
class ProductCachingTest {

    @Autowired
    private ProductQueryService queryService;

    @Autowired
    private ProductRepository productRepository;

    @Test
    @DirtiesContext  // Resets Spring context (and cache) between tests
    void findById_cachedOnSecondCall() {
        // First call: miss → DB
        queryService.findById(1L);
        // Second call: hit → cache
        queryService.findById(1L);

        // Verify DB was queried only once
        verify(productRepository, times(1)).findById(any());
    }
}
```

---

## Best Practices

### DO
- Cache only serializable DTOs/records, not JPA entities
- Define TTL per data type based on its volatility
- Invalidate cache on mutations (`@CacheEvict`)
- Use `unless = "#result == null"` to avoid caching null results
- Use JSON serialization (not native Java) for cross-version compatibility
- Monitor hit/miss rate — if hit rate < 70%, the cache is not adding value

### DON'T
- Cache JPA entities with lazy collections (`LazyInitializationException` + serialization issues)
- Set long TTLs on data that changes frequently
- Cache write operations (`@CachePut` on volatile `save()` calls)
- Forget `@EnableCaching` on the configuration class
- Implement cache-aside manually when Spring Cache annotations are sufficient

### When NOT to Cache
- Data that changes on every request (real-time)
- User-personalized data (use session cache instead)
- Data where temporary inconsistency is unacceptable

---

## Related Skills

- `spring-boot` — Redis configuration, application.yaml setup, and dependency management
- `jpa-patterns` — Avoid caching JPA entities directly; use DTOs as cache values
- `observability` — Cache hit/miss metrics with Micrometer and Spring Actuator
- `performance-optimization` — Caching is one of several performance strategies
- `spring-boot-testing` — Testing cache behavior with `@SpringBootTest` and `@DirtiesContext`
