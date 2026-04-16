---
name: grpc-design
description: Design and implement gRPC services with Protocol Buffers 4, Spring gRPC 1.x, and protobuf-maven-plugin in Java 25 microservices. Covers .proto file design, service implementation, observability, and dual REST+gRPC API patterns.
metadata:
  version: "1.2.0"
  domain: backend
  triggers: gRPC, Protocol Buffers, protobuf, Spring gRPC, RPC, binary API, grpc server
  role: specialist
  scope: implementation
---

# gRPC Design Skill

Design and implement gRPC services with Protocol Buffers 4, Spring gRPC 1.x, and Maven in Java 25 microservices.

## When to Use
- High-efficiency binary communication between services
- Internal APIs between microservices
- Bidirectional or server-side streaming
- Dual REST + gRPC exposure (one microservice, two adapters)
- When performance and strict typing take priority over HTTP readability

## Reference Stack

| Component | Version |
|-----------|---------|
| gRPC | 1.80.0 |
| spring-grpc | 1.0.2 |
| Protocol Buffers | 4.34.1 (protobuf-java) |
| protobuf-maven-plugin | 5.0.2 (io.github.ascopes) |
| grpc-census | 1.80.0 (observability) |

---

## gRPC Module Structure

```
catalog-infrastructure-api-grpc/
├── src/main/
│   ├── java/
│   │   └── io/github/icesoft/catalog/infrastructure/api/grpc/
│   │       ├── ProvinciaGrpcService.java    ← Service implementation
│   │       └── ProvinciaGrpcMapper.java     ← Mapper domain → protobuf messages
│   └── spec/
│       ├── catalog_common.proto             ← Shared messages
│       ├── province.proto                   ← Province service
│       └── product.proto                   ← Product service
└── pom.xml
```

---

## Maven: Compiling .proto Files

```xml
<!-- pom.xml of the api-grpc module -->
<build>
    <plugins>
        <plugin>
            <groupId>io.github.ascopes</groupId>
            <artifactId>protobuf-maven-plugin</artifactId>
            <version>${protobuf-maven-plugin.version}</version>  <!-- 5.0.2 -->
            <configuration>
                <!-- Directory containing .proto files -->
                <sourceDirectories>
                    <sourceDirectory>${project.basedir}/src/main/spec</sourceDirectory>
                </sourceDirectories>
                <!-- protoc compiler version -->
                <protoc>${protobuf-java.version}</protoc>  <!-- 4.34.1 -->
                <!-- Plugin to generate gRPC Java code -->
                <plugins>
                    <plugin kind="binary-maven">
                        <groupId>io.grpc</groupId>
                        <artifactId>protoc-gen-grpc-java</artifactId>
                        <version>${grpc.version}</version>  <!-- 1.80.0 -->
                    </plugin>
                </plugins>
            </configuration>
            <executions>
                <execution>
                    <id>generate</id>
                    <goals><goal>generate</goal></goals>
                </execution>
            </executions>
        </plugin>
    </plugins>
</build>
```

### Dependencias

```xml
<dependencies>
    <!-- Spring gRPC Server -->
    <dependency>
        <groupId>org.springframework.grpc</groupId>
        <artifactId>spring-grpc-server-spring-boot-starter</artifactId>
    </dependency>
    <!-- gRPC Census: automatic metrics and tracing -->
    <dependency>
        <groupId>io.grpc</groupId>
        <artifactId>grpc-census</artifactId>
    </dependency>
</dependencies>
```

---

## .proto File Design

### Shared Messages (catalog_common.proto)

```protobuf
syntax = "proto3";

package io.github.example.catalog.grpc;

option java_multiple_files = true;
option java_package = "io.github.example.catalog.infrastructure.api.grpc";

// Structured error (analogous to ProblemDetail from RFC 9457)
message ProblemDetail {
  string type = 1;
  string title = 2;
  int32 status = 3;
  string detail = 4;
  string instance = 5;
}

// Pagination metadata
message PageResult {
  int32 page = 1;
  int32 size = 2;
  int64 total_items = 3;
}
```

### Domain Service (product.proto)

```protobuf
syntax = "proto3";

package io.github.example.catalog.grpc;

option java_multiple_files = true;
option java_package = "io.github.example.catalog.infrastructure.api.grpc";

import "catalog_common.proto";

// Full detail message
message ProductDetail {
  int64 id = 1;
  string name = 2;
  double price = 3;
  string status = 4;
  string category_name = 5;
}

// Summary message (for lists)
message ProductSummary {
  int64 id = 1;
  string name = 2;
  double price = 3;
}

// Request for paginated listing
message ListProductsRequest {
  string status = 1;    // Optional filter
  int32 page = 2;       // 0-based
  int32 size = 3;       // Page size (default 20)
}

// Paginated response
message ListProductsResponse {
  repeated ProductSummary items = 1;
  PageResult pagination = 2;
}

message GetProductByIdRequest {
  int64 id = 1;
}

// Service definition
service ProductService {
  // Unary RPC
  rpc ListProducts(ListProductsRequest) returns (ListProductsResponse);
  rpc GetProductById(GetProductByIdRequest) returns (ProductDetail);

  // Server streaming (for large result sets)
  rpc StreamProducts(ListProductsRequest) returns (stream ProductSummary);
}
```

### proto3 Conventions

```protobuf
// ✅ snake_case for fields
message ProductRequest {
  string product_name = 1;    // ✅
  string productName = 2;     // ❌
}

// ✅ PascalCase for messages and services
message ProductDetail { }     // ✅
message product_detail { }    // ❌

// ✅ Dedicated request/response messages per RPC
// Do not reuse messages across different RPCs — enables independent evolution
message GetProductByIdRequest { int64 id = 1; }
message GetProductBySku { string sku = 1; }   // Separado

// ✅ Reserve removed fields to prevent accidental reuse
message Product {
  reserved 3, 4;
  reserved "old_field_name";
}
```

---

## Service Implementation (Spring gRPC)

```java
@GrpcService  // Spring gRPC: automatically registers the gRPC service
public class ProductGrpcService extends ProductServiceGrpc.ProductServiceImplBase {

    private final ProductQueryService queryService;
    private final ProductGrpcMapper mapper;

    public ProductGrpcService(ProductQueryService queryService, ProductGrpcMapper mapper) {
        this.queryService = queryService;
        this.mapper = mapper;
    }

    @Override
    public void listProducts(ListProductsRequest request,
                              StreamObserver<ListProductsResponse> responseObserver) {
        try {
            var products = queryService.findByStatus(request.getStatus());
            var response = ListProductsResponse.newBuilder()
                .addAllItems(products.stream().map(mapper::toSummary).toList())
                .setPagination(PageResult.newBuilder()
                    .setPage(0)
                    .setSize(products.size())
                    .setTotalItems(products.size())
                    .build())
                .build();

            responseObserver.onNext(response);
            responseObserver.onCompleted();
        } catch (Exception e) {
            responseObserver.onError(
                Status.INTERNAL
                    .withDescription(e.getMessage())
                    .withCause(e)
                    .asRuntimeException()
            );
        }
    }

    @Override
    public void getProductById(GetProductByIdRequest request,
                                StreamObserver<ProductDetail> responseObserver) {
        queryService.findById(new ProductId(request.getId()))
            .ifPresentOrElse(
                product -> {
                    responseObserver.onNext(mapper.toDetail(product));
                    responseObserver.onCompleted();
                },
                () -> responseObserver.onError(
                    Status.NOT_FOUND
                        .withDescription("Product not found: " + request.getId())
                        .asRuntimeException()
                )
            );
    }

    @Override
    public void streamProducts(ListProductsRequest request,
                                StreamObserver<ProductSummary> responseObserver) {
        // Server streaming: each product is sent individually
        queryService.findByStatus(request.getStatus()).forEach(product -> {
            responseObserver.onNext(mapper.toSummary(product));
        });
        responseObserver.onCompleted();
    }
}
```

---

## Mapper Domain → Protobuf (MapStruct)

```java
@Mapper(componentModel = "spring")
public interface ProductGrpcMapper {

    @Mapping(target = "id", source = "id.value")
    @Mapping(target = "categoryName", source = "category.name")
    ProductDetail toDetail(Product product);

    @Mapping(target = "id", source = "id.value")
    ProductSummary toSummary(Product product);

    // Unmapped proto3 fields default to zero values (0, "", false)
    // No null handling needed — proto3 has no null
}
```

---

## Spring Boot Configuration

```yaml
# application.yaml
spring:
  grpc:
    server:
      port: ${GRPC_SERVER_PORT:9090}
      reflection:
        enabled: true  # Enables gRPC Server Reflection (required by grpcurl)
```

```java
// In @SpringBootApplication or @Configuration
@Bean
public ServerInterceptor loggingInterceptor() {
    // Interceptor for logging gRPC calls
    return new LoggingServerInterceptor();
}
```

---

## gRPC Status Codes

Mapping domain exceptions to gRPC Status codes:

```java
// Utility to map domain exceptions to gRPC Status
public static Status toGrpcStatus(RuntimeException ex) {
    return switch (ex) {
        case EntityNotFoundException e -> Status.NOT_FOUND.withDescription(e.getMessage());
        case IllegalArgumentException e -> Status.INVALID_ARGUMENT.withDescription(e.getMessage());
        case AccessDeniedException e   -> Status.PERMISSION_DENIED.withDescription(e.getMessage());
        default                        -> Status.INTERNAL.withDescription(ex.getMessage()).withCause(ex);
    };
}
```

| gRPC Status | HTTP Equivalent | Use When |
|-------------|----------------|----------|
| `OK` | 200 | Success |
| `NOT_FOUND` | 404 | Entity not found |
| `INVALID_ARGUMENT` | 400 | Invalid request |
| `ALREADY_EXISTS` | 409 | Duplicate resource |
| `PERMISSION_DENIED` | 403 | Insufficient permissions |
| `UNAUTHENTICATED` | 401 | Not authenticated |
| `INTERNAL` | 500 | Internal error |
| `UNAVAILABLE` | 503 | Service not available |

---

## Observability: gRPC Census

With `grpc-census`, metrics are recorded automatically:

```xml
<dependency>
    <groupId>io.grpc</groupId>
    <artifactId>grpc-census</artifactId>
</dependency>
```

Metrics available via Micrometer/Prometheus:
- `grpc.server.received_messages_per_rpc`
- `grpc.server.sent_messages_per_rpc`
- `grpc.server.server_latency`
- `grpc.server.started_rpcs`

---

## Testing with grpcurl

```bash
# List services (requires server reflection enabled)
grpcurl -plaintext localhost:9090 list

# List methods of a service
grpcurl -plaintext localhost:9090 list io.github.example.catalog.grpc.ProductService

# Call a method
grpcurl -plaintext \
  -d '{"status": "ACTIVE", "page": 0, "size": 20}' \
  localhost:9090 \
  io.github.example.catalog.grpc.ProductService/ListProducts

# Obtener por ID
grpcurl -plaintext \
  -d '{"id": 1}' \
  localhost:9090 \
  io.github.example.catalog.grpc.ProductService/GetProductById
```

---

## Dual API: REST + gRPC

In hexagonal architecture, both adapters call the same Application Service:

```
Application Service (ProductQueryService)
    ↑                         ↑
REST Adapter              gRPC Adapter
(ProductsApiDelegateImpl) (ProductGrpcService)
    ↑                         ↑
openapi.yaml             product.proto
(openapi-generator)      (protobuf-maven-plugin)
```

**Benefits:**
- REST for UI and external clients
- gRPC for high-performance inter-microservice communication
- Single business layer, two adapters

---

## Best Practices

### .proto Design
- One `.proto` file per bounded context/service
- Shared messages in `catalog_common.proto` (or similar)
- `java_multiple_files = true` — one .java file per message
- Use `reserved` for removed fields
- Unique request/response messages per RPC (enables independent evolution)
- snake_case for fields, PascalCase for messages and services

### Implementation
- Always close `StreamObserver` (`onCompleted` or `onError`) — never leave it open
- Map domain exceptions to appropriate gRPC `Status` codes
- Use interceptors for cross-cutting concerns (auth, logging, tracing)
- Enable `reflection.enabled: true` in development for grpcurl

### API Evolution
- Adding new fields is always backward compatible in proto3
- Never change existing field numbers
- Never remove fields — use `reserved` instead
- Never change the type of an existing field

---

## Related Skills

- `spring-boot` — Multi-module Maven setup, Spring gRPC configuration, application.yaml
- `openapi-spec-generation` — Design-first REST alongside gRPC (dual adapter pattern)
- `observability` — gRPC Census metrics with Micrometer and Prometheus
- `clean-ddd-hexagonal` — Hexagonal architecture with REST and gRPC adapters sharing one application layer
- `springboot-security` — Securing gRPC endpoints with interceptors and JWT validation
