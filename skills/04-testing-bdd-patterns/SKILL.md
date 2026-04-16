---
name: bdd-patterns
user-invocable: false
description: Use when applying Behavior-Driven Development patterns with Cucumber 7, Spring Boot 4, JUnit Platform Suite, and Testcontainers. Covers Given-When-Then structure, feature files, step definitions, and Spring integration for Java microservices.
metadata:
  version: "1.2.0"
  domain: backend
  triggers: BDD, Cucumber, Gherkin, behavior-driven, Given-When-Then, acceptance tests, feature files, step definitions, Testcontainers
  role: specialist
  scope: implementation
allowed-tools:
  - Bash
  - Read
---

# BDD Patterns

Behavior-Driven Development with Cucumber 7, Spring Boot 4, and Testcontainers for Java 25 microservices.

## When to Use

- Writing acceptance tests that describe business behavior
- Collaborating with non-technical stakeholders on test scenarios
- Validating end-to-end application flows with real infrastructure
- Establishing a ubiquitous language between developers and domain experts

## Reference Stack

| Component | Version |
|-----------|---------|
| Cucumber | 7.34.3 |
| cucumber-spring | 7.34.3 |
| cucumber-junit-platform-engine | 7.34.3 |
| junit-platform-suite | 1.12.2 |
| Testcontainers | 1.21.0 |
| Spring Boot Test | 4.0.x |

---

## BDD Module Structure

BDD tests live in the `application` module (application layer):

```
catalog-application/
├── src/
│   ├── main/java/...
│   └── test/
│       ├── java/
│       │   └── io/github/icesoft/catalog/application/
│       │       ├── cucumber/
│       │       │   ├── CucumberSpringConfig.java  ← Spring context for Cucumber
│       │       │   └── steps/
│       │       │       └── ProductStepDefinitions.java
│       │       └── runner/
│       │           └── ProductRunnerTest.java     ← JUnit Platform Suite
│       └── resources/
│           └── features/
│               └── product/
│                   └── create-product.feature
```

---

## Maven Dependencies

```xml
<!-- In application/pom.xml -->
<dependencies>
    <!-- Cucumber -->
    <dependency>
        <groupId>io.cucumber</groupId>
        <artifactId>cucumber-java</artifactId>
        <version>${cucumber.version}</version>
        <scope>test</scope>
    </dependency>
    <dependency>
        <groupId>io.cucumber</groupId>
        <artifactId>cucumber-spring</artifactId>
        <version>${cucumber.version}</version>
        <scope>test</scope>
    </dependency>
    <dependency>
        <groupId>io.cucumber</groupId>
        <artifactId>cucumber-junit-platform-engine</artifactId>
        <version>${cucumber.version}</version>
        <scope>test</scope>
    </dependency>

    <!-- JUnit Platform Suite for runners -->
    <dependency>
        <groupId>org.junit.platform</groupId>
        <artifactId>junit-platform-suite</artifactId>
        <version>${junit-platform-suite.version}</version>
        <scope>test</scope>
    </dependency>

    <!-- Testcontainers -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-testcontainers</artifactId>
        <scope>test</scope>
    </dependency>
    <dependency>
        <groupId>org.testcontainers</groupId>
        <artifactId>postgresql</artifactId>
        <scope>test</scope>
    </dependency>
</dependencies>
```

---

## Feature Files (Gherkin)

### Given-When-Then Structure

Feature files should use the domain's ubiquitous language. Scenarios may be written in any language — use the language that best communicates the business intent to stakeholders.

```gherkin
Feature: Product Management
  As a catalog administrator
  I want to manage products
  So that I can keep the catalog up to date

  Background:
    Given the catalog service is available

  Scenario: Create a valid product
    Given no product with name "Widget Pro" exists
    When I create a product with name "Widget Pro" and price 29.99
    Then the product is created successfully
    And the product has status "ACTIVE"

  Scenario: Cannot create product with negative price
    When I attempt to create a product with name "Widget" and price -5.00
    Then the creation fails with a validation error
    And the error message states "Price must be positive"

  Scenario Outline: Create products in different categories
    When I create a product with name "<name>" and price <price>
    Then the product is created successfully

    Examples:
      | name            | price |
      | Basic Widget    | 9.99  |
      | Premium Widget  | 49.99 |
      | Ultimate Widget | 99.99 |
```

### Domain-language feature (Spanish domain example)

```gherkin
Feature: Consulta de Provincias
  Como usuario del API
  Quiero consultar provincias españolas
  Para obtener información geográfica

  Scenario: Listar todas las provincias
    When consulto la lista de provincias
    Then obtengo al menos 50 provincias
    And todas las provincias tienen un código y nombre

  Scenario: Obtener provincia por código
    When consulto la provincia con código "28"
    Then obtengo la provincia "Madrid"
    And la provincia pertenece a la comunidad "Comunidad de Madrid"
```

---

## Spring Configuration for Cucumber

```java
// CucumberSpringConfig.java — activates Spring context in Cucumber
@CucumberContextConfiguration
@SpringBootTest(
    classes = CatalogApplicationTestConfig.class,
    webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT
)
public class CucumberSpringConfig {
    // Intentionally empty: only activates Cucumber-Spring integration
}

// Test config with Testcontainers
@TestConfiguration
@EnableAutoConfiguration
public class CatalogApplicationTestConfig {

    @Bean
    @ServiceConnection  // Spring Boot 4: auto-configures datasource
    PostgreSQLContainer<?> postgresContainer() {
        return new PostgreSQLContainer<>("postgres:16-alpine")
            .withDatabaseName("catalog_test")
            .withUsername("test")
            .withPassword("test");
    }

    @Bean
    @ServiceConnection  // Spring Boot 4: auto-configures Redis
    GenericContainer<?> redisContainer() {
        return new GenericContainer<>("redis:8.0-alpine")
            .withExposedPorts(6379);
    }
}
```

---

## Step Definitions

```java
@Component  // Spring manages the step lifecycle
public class ProductStepDefinitions {

    @Autowired
    private ProductService productService;

    @Autowired
    private ProductRepository productRepository;

    @Autowired
    private TestRestTemplate restTemplate;

    private ResponseEntity<?> lastResponse;

    @Given("no product with name {string} exists")
    public void noProductWithNameExists(String name) {
        productRepository.deleteByName(name);
    }

    @When("I create a product with name {string} and price {double}")
    public void createProduct(String name, double price) {
        var request = new CreateProductRequest(name, BigDecimal.valueOf(price));
        lastResponse = restTemplate.postForEntity("/api/v1/products", request, ProductDto.class);
    }

    @When("I attempt to create a product with name {string} and price {double}")
    public void attemptToCreateProduct(String name, double price) {
        var request = new CreateProductRequest(name, BigDecimal.valueOf(price));
        lastResponse = restTemplate.postForEntity("/api/v1/products", request, Map.class);
    }

    @Then("the product is created successfully")
    public void productIsCreatedSuccessfully() {
        assertThat(lastResponse.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        assertThat(lastResponse.getBody()).isNotNull();
    }

    @Then("the product has status {string}")
    public void productHasStatus(String status) {
        ProductDto product = (ProductDto) lastResponse.getBody();
        assertThat(product.getStatus()).isEqualTo(status);
    }

    @Then("the creation fails with a validation error")
    public void creationFailsWithValidationError() {
        assertThat(lastResponse.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
    }

    @Then("the error message states {string}")
    public void errorMessageStates(String message) {
        Map<?, ?> body = (Map<?, ?>) lastResponse.getBody();
        assertThat(body.get("detail").toString()).contains(message);
    }

    @After
    public void cleanup() {
        // Reset state between scenarios
        lastResponse = null;
    }
}
```

---

## Test Runner (JUnit Platform Suite)

```java
// One runner per feature group or domain
@Suite
@IncludeEngines("cucumber")
@SelectClasspathResource("features/product")
@ConfigurationParameter(
    key = GLUE_PROPERTY_NAME,
    value = "io.github.example.application.cucumber"
)
@ConfigurationParameter(
    key = PLUGIN_PROPERTY_NAME,
    value = "pretty, json:target/cucumber-reports/product.json, html:target/cucumber-reports/product.html"
)
public class ProductRunnerTest {}
```

### cucumber.properties

```properties
cucumber.publish.quiet=true
cucumber.execution.parallel.enabled=false
cucumber.junit-platform.naming-strategy=long
```

---

## Testcontainers: @ServiceConnection (Spring Boot 4)

```java
// Spring Boot 4 with @ServiceConnection: no @DynamicPropertySource needed
@TestConfiguration
public class TestContainersConfig {

    @Bean
    @ServiceConnection  // Auto-configures spring.datasource.*
    static PostgreSQLContainer<?> postgresContainer() {
        return new PostgreSQLContainer<>("postgres:16-alpine");
    }

    @Bean
    @ServiceConnection  // Auto-configures spring.data.redis.*
    static GenericContainer<?> redisContainer() {
        return new GenericContainer<>("redis:8.0-alpine")
            .withExposedPorts(6379);
    }
}
```

---

## Best Practices

### Feature Files
- Write from the user/business perspective — describe **what**, not **how**
- One scenario = one behavior
- Use `Background` for common preconditions
- Use `Scenario Outline` for same behavior with multiple data sets
- Use declarative language (what), not imperative (how)
- Name features using domain language (DDD ubiquitous language)

### Step Definitions
- Annotate with `@Component` — Spring manages the instance lifecycle
- One method per step; avoid conditional logic inside steps
- Store state between steps in class fields (Cucumber creates a new instance per scenario)
- Use `@After` to clean up state between scenarios
- Use AssertJ for fluent assertions (`assertThat`)

### Organization
- Group `features/` by domain or functionality
- One `*RunnerTest.java` per related feature group
- One `CucumberSpringConfig` per test project

## Anti-patterns

❌ Avoid:
- Steps describing UI clicks (too coupled to implementation)
- Business logic in step definitions (belongs in the service layer)
- Shared state between features (each scenario must be independent)
- Overly long feature files — split by behavior

✅ Instead:
- Describe observable outcomes, not implementation details
- Delegate business logic to application services
- Keep each scenario fully self-contained with `Background` or setup steps
- One scenario per distinct business rule

---

## Related Skills

- `spring-boot-testing` — Unit and integration test patterns with `@SpringBootTest`, `@DataJpaTest`, `@WebMvcTest`
- `test-driven-development` — TDD cycle for unit and integration tests before BDD acceptance tests
- `test-quality` — Test quality criteria, coverage, and test pyramid guidelines
- `spring-boot` — Application setup, module structure, and Testcontainers integration
