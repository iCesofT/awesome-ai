---
name: openapi-spec-generation
description: Generate and maintain OpenAPI 3.x specifications with design-first approach and Spring Boot code generation using openapi-generator-maven-plugin with delegate pattern. Use when creating API documentation, generating Spring controllers from specs, or ensuring API contract compliance.
metadata:
  version: "1.2.0"
  domain: backend
  triggers: OpenAPI, OpenAPI 3.x, API documentation, Swagger, openapi-generator, design-first, Spring Boot API
  role: specialist
  scope: implementation
---

# OpenAPI Spec Generation

Patterns for designing, maintaining, and generating code from OpenAPI specifications in Spring Boot 4 projects with hexagonal architecture.

## When to Use

- Designing API contracts (design-first approach)
- Generating Spring controllers from OpenAPI specs
- Configuring `openapi-generator-maven-plugin`
- Validating implementation against the API contract
- Exposing API docs with SpringDoc + Swagger UI

## Approach: Design-First with Delegate Pattern

In hexagonal architecture:
1. **Write the spec** `openapi.yaml` first (the contract)
2. **Generate** interfaces + DTOs with `openapi-generator-maven-plugin`
3. **Implement** the delegate with business logic
4. **Expose** the UI with SpringDoc

```
catalog-infrastructure-api-rest/
  ├── src/main/spec/openapi.yaml        ← Hand-crafted spec
  └── src/main/java/
      ├── [generated] ProductsApi.java    ← Controller interface
      ├── [generated] ProductsApiDelegate.java
      ├── [generated] ProductDto.java     ← DTOs with "Dto" suffix
      ├── ProductsApiController.java     ← Implements ProductsApi
      └── ProductsApiDelegateImpl.java   ← Your business logic
```

---

## Maven Plugin Configuration

```xml
<!-- pom.xml of the api-rest module -->
<plugin>
    <groupId>org.openapitools</groupId>
    <artifactId>openapi-generator-maven-plugin</artifactId>
    <version>${openapi-generator-maven-plugin.version}</version>  <!-- 7.21.0 -->
    <executions>
        <execution>
            <id>generate-api</id>
            <goals><goal>generate</goal></goals>
            <configuration>
                <inputSpec>${project.basedir}/src/main/spec/openapi.yaml</inputSpec>
                <generatorName>spring</generatorName>
                <library>spring-boot</library>
                <addCompileSourceRoot>true</addCompileSourceRoot>

                <!-- Generated packages -->
                <apiPackage>${package.name}.apimodel.api</apiPackage>
                <modelPackage>${package.name}.apimodel.model</modelPackage>
                <modelNameSuffix>Dto</modelNameSuffix>

                <!-- Do not generate tests or docs (written by hand) -->
                <generateApiDocumentation>false</generateApiDocumentation>
                <generateApiTests>false</generateApiTests>
                <generateModelDocumentation>false</generateModelDocumentation>
                <generateModelTests>false</generateModelTests>
                <supportingFilesToGenerate>ApiUtil.java</supportingFilesToGenerate>

                <configOptions>
                    <!-- Jakarta EE (Spring Boot 4 uses Jakarta, not javax) -->
                    <useJakartaEe>true</useJakartaEe>
                    <basePackage>${package.name}</basePackage>
                    <configPackage>${package.name}.apimodel.config</configPackage>

                    <!-- Delegate pattern: generates interface + delegate to implement -->
                    <interfaceOnly>false</interfaceOnly>
                    <delegatePattern>true</delegatePattern>

                    <dateLibrary>java8-localdatetime</dateLibrary>
                    <useBeanValidation>false</useBeanValidation>   <!-- Validation handled in domain layer -->
                    <performBeanValidation>false</performBeanValidation>
                    <useSwaggerUI>false</useSwaggerUI>             <!-- SpringDoc manages the UI -->
                </configOptions>
            </configuration>
        </execution>
    </executions>
</plugin>
```

### Required Dependencies

```xml
<!-- In the api-rest module -->
<dependency>
    <groupId>io.swagger.core.v3</groupId>
    <artifactId>swagger-annotations</artifactId>
    <version>${swagger-annotations-v3.version}</version>  <!-- 2.2.45 -->
</dependency>
<dependency>
    <groupId>org.springdoc</groupId>
    <artifactId>springdoc-openapi-starter-webmvc-ui</artifactId>
    <version>${springdoc-openapi.version}</version>  <!-- 3.0.2 -->
</dependency>
<dependency>
    <groupId>org.openapitools</groupId>
    <artifactId>jackson-databind-nullable</artifactId>
    <version>${jackson-databind-nullable.version}</version>  <!-- 0.2.10 -->
</dependency>
```

### SpringDoc en application.yaml

```yaml
springdoc:
  api-docs:
    enabled: ${SPRINGDOC_API_DOCS_ENABLED:true}
    path: /openapi/api-docs
  swagger-ui:
    enabled: ${SPRINGDOC_SWAGGER_UI_ENABLED:true}
    path: /openapi/ui.html
```

---

## Delegate Pattern: Implementation

### Controller (Generated → delegates only)

```java
// Your code: minimal wrapper over generated code
@RestController
public class ProductsApiController implements ProductsApi {
    private final ProductsApiDelegate delegate;

    public ProductsApiController(ProductsApiDelegate delegate) {
        this.delegate = delegate;
    }

    @Override
    public ResponseEntity<List<ProductDto>> listProducts(
            @Valid @RequestParam(required = false) String status) {
        return delegate.listProducts(status);
    }

    @Override
    public ResponseEntity<ProductDto> createProduct(
            @Valid @RequestBody CreateProductDto request) {
        return delegate.createProduct(request);
    }
}
```

### Delegate (Your actual business logic)

```java
@Component
public class ProductsApiDelegateImpl implements ProductsApiDelegate {
    private final ProductQueryService queryService;
    private final ProductCommandService commandService;
    private final ProductApiMapper mapper;

    // Constructor injection

    @Override
    public ResponseEntity<List<ProductDto>> listProducts(String status) {
        List<Product> products = queryService.findByStatus(status);
        return ResponseEntity.ok(products.stream().map(mapper::toDto).toList());
    }

    @Override
    public ResponseEntity<ProductDto> createProduct(CreateProductDto request) {
        var command = mapper.toCommand(request);
        Product product = commandService.create(command);
        return ResponseEntity.status(HttpStatus.CREATED).body(mapper.toDto(product));
    }
}
```

### Mapper API ↔ Domain (MapStruct)

```java
@Mapper(componentModel = "spring")
public interface ProductApiMapper {
    ProductDto toDto(Product product);
    CreateProductCommand toCommand(CreateProductDto dto);
}
```

---

## OpenAPI 3.0 Spec Template

```yaml
openapi: 3.0.3
info:
  title: Products API
  version: 1.0.0
  description: |
    API for product management.

    ## Authentication
    Bearer JWT token required on all protected operations.
  contact:
    name: API Support
    email: api@example.com

servers:
  - url: http://localhost:8080/api/v1
    description: Local development
  - url: https://api.example.com/v1
    description: Production

tags:
  - name: Products
    description: Product management

paths:
  /products:
    get:
      operationId: listProducts
      summary: List products
      tags: [Products]
      parameters:
        - name: status
          in: query
          required: false
          schema:
            $ref: "#/components/schemas/ProductStatus"
        - $ref: "#/components/parameters/PageParam"
        - $ref: "#/components/parameters/LimitParam"
      responses:
        "200":
          description: List of products
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ProductListResponse"
        "400":
          $ref: "#/components/responses/BadRequest"
        "401":
          $ref: "#/components/responses/Unauthorized"

    post:
      operationId: createProduct
      summary: Create product
      tags: [Products]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/CreateProductRequest"
      responses:
        "201":
          description: Product created
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Product"
          headers:
            Location:
              description: URL of the created resource
              schema:
                type: string
                format: uri
        "400":
          $ref: "#/components/responses/BadRequest"

  /products/{productId}:
    parameters:
      - $ref: "#/components/parameters/ProductIdParam"

    get:
      operationId: getProductById
      summary: Get product by ID
      tags: [Products]
      responses:
        "200":
          description: Product
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Product"
        "404":
          $ref: "#/components/responses/NotFound"

components:
  schemas:
    Product:
      type: object
      required: [id, name, price, status]
      properties:
        id:
          type: integer
          format: int64
          readOnly: true
        name:
          type: string
          minLength: 1
          maxLength: 100
        price:
          type: number
          format: double
          minimum: 0
        status:
          $ref: "#/components/schemas/ProductStatus"
        createdAt:
          type: string
          format: date-time
          readOnly: true

    ProductStatus:
      type: string
      enum: [ACTIVE, INACTIVE, DISCONTINUED]

    CreateProductRequest:
      type: object
      required: [name, price]
      properties:
        name:
          type: string
          minLength: 1
          maxLength: 100
        price:
          type: number
          format: double
          minimum: 0

    ProductListResponse:
      type: object
      required: [items, pagination]
      properties:
        items:
          type: array
          items:
            $ref: "#/components/schemas/Product"
        pagination:
          $ref: "#/components/schemas/Pagination"

    Pagination:
      type: object
      required: [page, size, totalItems]
      properties:
        page:
          type: integer
          minimum: 0
        size:
          type: integer
          minimum: 1
          maximum: 100
        totalItems:
          type: integer
          minimum: 0

    ProblemDetail:
      type: object
      required: [status, title]
      properties:
        type:
          type: string
          format: uri
        title:
          type: string
        status:
          type: integer
        detail:
          type: string
        instance:
          type: string
          format: uri

  parameters:
    ProductIdParam:
      name: productId
      in: path
      required: true
      schema:
        type: integer
        format: int64

    PageParam:
      name: page
      in: query
      schema:
        type: integer
        minimum: 0
        default: 0

    LimitParam:
      name: size
      in: query
      schema:
        type: integer
        minimum: 1
        maximum: 100
        default: 20

  responses:
    BadRequest:
      description: Invalid request
      content:
        application/problem+json:
          schema:
            $ref: "#/components/schemas/ProblemDetail"

    Unauthorized:
      description: Authentication required
      content:
        application/problem+json:
          schema:
            $ref: "#/components/schemas/ProblemDetail"

    NotFound:
      description: Resource not found
      content:
        application/problem+json:
          schema:
            $ref: "#/components/schemas/ProblemDetail"

  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

security:
  - bearerAuth: []
```

---

## Best Practices

### Do's

- **Design-First**: Write the spec before the code
- **`$ref`**: Reuse schemas, parameters, and responses
- **`operationId`**: Unique per endpoint — used as the generated method name
- **`modelNameSuffix: Dto`**: Distinguishes generated DTOs from domain objects
- **`delegatePattern: true`**: Separates generated interface from your implementation
- **`useJakartaEe: true`**: Required for Spring Boot 4
- **Error content-type**: Use `application/problem+json` (RFC 9457) for error responses
- **Versioning**: In the URL (`/api/v1`) or in `info.version`

### Don'ts

- **Do not use `interfaceOnly: true`** with hexagonal — `delegatePattern` is cleaner
- **Do not hardcode URLs** in the spec — use server variables
- **Do not mix `null` and `required`** without being explicit
- **Do not regenerate tests** — disable with `generateApiTests: false`
- **Do not skip security** — define `securitySchemes` and apply `security` on operations

---

## Related Skills

- `api-design` — REST API design principles, versioning, pagination, and error conventions
- `spring-boot` — Spring Boot 4 module structure and controller configuration
- `grpc-design` — gRPC service design alongside OpenAPI (dual adapter pattern)
- `spec-driven-development` — Using OpenAPI specs to drive development from contracts
- `springboot-security` — Securing generated API endpoints with Spring Security 6
