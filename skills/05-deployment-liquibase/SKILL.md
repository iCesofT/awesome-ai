---
name: liquibase
description: Database schema migration management with Liquibase 5 and Spring Boot 4. Covers changelog structure (DDL/DML separation), Maven plugin for offline SQL generation, rollback, and best practices for hexagonal microservices.
metadata:
  version: "1.2.0"
  domain: backend
  triggers: Liquibase, database migration, schema migration, changelog, DDL, DML, flyway alternative
  role: specialist
  scope: implementation
---

# Liquibase Skill

Schema migration management with Liquibase 5 + Spring Boot 4 + PostgreSQL. Covers DDL/DML separation, offline SQL generation, rollback, and multi-module project structure.

## When to Use

- Creating or modifying tables, indexes, or constraints
- Loading reference data (DML)
- Reviewing migrations before deployment
- Configuring Liquibase in a Spring Boot project
- Generating offline SQL for PR review and audit

## Reference Stack

| Component | Version |
|-----------|---------|
| Liquibase | 5.0.2 |
| liquibase-maven-plugin | 5.0.2 |
| spring-boot-starter-liquibase | 4.0.x |
| PostgreSQL | 16 |

---

## File Structure

```
catalog-infrastructure-persistence-jpa/
└── src/main/liquibase/
    ├── db.changelog-master.xml       ← Master file that includes all changesets
    └── changelog/
        ├── ddl/                      ← Data Definition Language (schema)
        │   ├── 001-ddl-create-product-table.xml
        │   ├── 002-ddl-create-category-table.xml
        │   └── 003-ddl-add-product-category-fk.xml
        └── dml/                      ← Data Manipulation Language (data)
            ├── 101-dml-load-category-data.xml
            └── 102-dml-load-product-seed-data.xml
```

**Naming convention:**
- `NNN-type-description.xml`
- DDL: numbering `001-099`
- DML: numbering `101-199`
- Evolutionary DDL: numbering `200-299`
- Evolutionary DML: numbering `300-399`
- Never modify already-applied changesets — add new ones instead

---

## Master Changelog

```xml
<?xml version="1.0" encoding="UTF-8"?>
<databaseChangeLog
    xmlns="http://www.liquibase.org/xml/ns/dbchangelog"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:ext="http://www.liquibase.org/xml/ns/dbchangelog-ext"
    xsi:schemaLocation="http://www.liquibase.org/xml/ns/dbchangelog
                        https://www.liquibase.org/xml/ns/dbchangelog/dbchangelog-4.29.xsd
                        http://www.liquibase.org/xml/ns/dbchangelog-ext
                        https://www.liquibase.org/xml/ns/dbchangelog/dbchangelog-ext.xsd">

    <!-- DDL: Tables in dependency order (parent before child) -->
    <include file="changelog/ddl/001-ddl-create-category-table.xml"/>
    <include file="changelog/ddl/002-ddl-create-product-table.xml"/>

    <!-- DML: Reference data -->
    <include file="changelog/dml/101-dml-load-category-data.xml"/>
    <include file="changelog/dml/102-dml-load-product-seed-data.xml"/>

</databaseChangeLog>
```

---

## DDL Changeset: Create Table

```xml
<?xml version="1.0" encoding="UTF-8"?>
<databaseChangeLog
    xmlns="http://www.liquibase.org/xml/ns/dbchangelog"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.liquibase.org/xml/ns/dbchangelog
                        https://www.liquibase.org/xml/ns/dbchangelog/dbchangelog-4.29.xsd">

    <changeSet id="002-create-product-table" author="liquibase" labels="ddl">
        <createTable tableName="PRODUCT">
            <column name="ID" type="BIGINT" autoIncrement="true">
                <constraints primaryKey="true" nullable="false"/>
            </column>
            <column name="NAME" type="VARCHAR(100)">
                <constraints nullable="false"/>
            </column>
            <column name="PRICE" type="DECIMAL(10,2)">
                <constraints nullable="false"/>
            </column>
            <column name="STATUS" type="VARCHAR(20)" defaultValue="ACTIVE">
                <constraints nullable="false"/>
            </column>
            <column name="CATEGORY_ID" type="BIGINT">
                <constraints nullable="true"/>
            </column>
            <column name="CREATED_AT" type="TIMESTAMP" defaultValueComputed="CURRENT_TIMESTAMP">
                <constraints nullable="false"/>
            </column>
            <column name="VERSION" type="BIGINT" defaultValueNumeric="0">
                <constraints nullable="false"/>
            </column>
        </createTable>

        <!-- Indexes for frequent queries -->
        <createIndex indexName="IDX_PRODUCT_STATUS" tableName="PRODUCT">
            <column name="STATUS"/>
        </createIndex>
        <createIndex indexName="IDX_PRODUCT_CATEGORY_ID" tableName="PRODUCT">
            <column name="CATEGORY_ID"/>
        </createIndex>

        <!-- Foreign key -->
        <addForeignKeyConstraint
            baseTableName="PRODUCT"
            baseColumnNames="CATEGORY_ID"
            constraintName="FK_PRODUCT_CATEGORY"
            referencedTableName="CATEGORY"
            referencedColumnNames="ID"
            onDelete="SET NULL"/>

        <!-- Explicit rollback -->
        <rollback>
            <dropTable tableName="PRODUCT"/>
        </rollback>
    </changeSet>

</databaseChangeLog>
```

---

## DDL Changeset: Add Column

```xml
<changeSet id="003-add-product-sku" author="liquibase" labels="ddl">
    <addColumn tableName="PRODUCT">
        <column name="SKU" type="VARCHAR(50)">
            <constraints nullable="true" unique="true"/>
        </column>
    </addColumn>

    <!-- Create unique index for SKU -->
    <createIndex indexName="UQ_PRODUCT_SKU" tableName="PRODUCT" unique="true">
        <column name="SKU"/>
    </createIndex>

    <rollback>
        <dropIndex indexName="UQ_PRODUCT_SKU" tableName="PRODUCT"/>
        <dropColumn tableName="PRODUCT" columnName="SKU"/>
    </rollback>
</changeSet>
```

---

## DML Changeset: Load Reference Data

```xml
<?xml version="1.0" encoding="UTF-8"?>
<databaseChangeLog
    xmlns="http://www.liquibase.org/xml/ns/dbchangelog"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.liquibase.org/xml/ns/dbchangelog
                        https://www.liquibase.org/xml/ns/dbchangelog/dbchangelog-4.29.xsd">

    <changeSet id="101-load-category-data" author="liquibase" labels="dml">
        <insert tableName="CATEGORY">
            <column name="ID" valueNumeric="1"/>
            <column name="CODE" value="ELECTRONICS"/>
            <column name="NAME" value="Electronics"/>
        </insert>
        <insert tableName="CATEGORY">
            <column name="ID" valueNumeric="2"/>
            <column name="CODE" value="CLOTHING"/>
            <column name="NAME" value="Clothing"/>
        </insert>

        <rollback>
            <delete tableName="CATEGORY">
                <where>ID IN (1, 2)</where>
            </delete>
        </rollback>
    </changeSet>

</databaseChangeLog>
```

### CSV load (for large datasets)

```xml
<changeSet id="102-load-product-data-from-csv" author="liquibase" labels="dml">
    <loadData tableName="PRODUCT"
              file="data/products.csv"
              encoding="UTF-8"
              separator=","
              quotchar='"'>
        <column name="ID"     type="NUMERIC"/>
        <column name="NAME"   type="STRING"/>
        <column name="PRICE"  type="NUMERIC"/>
        <column name="STATUS" type="STRING"/>
    </loadData>
</changeSet>
```

---

## Spring Boot Integration

### application.yaml

```yaml
spring:
  liquibase:
    change-log: classpath:/liquibase/db.changelog-master.xml
    enabled: true
    # With Testcontainers: Liquibase runs automatically on startup
  jpa:
    hibernate:
      ddl-auto: validate  # ← Never create/update in production; Liquibase owns the schema
```

### Maven Dependency

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-liquibase</artifactId>
</dependency>
```

---

## Maven Plugin: Offline SQL Generation

Generate the migration SQL without a live database connection (useful for PR review and deployment pipelines):

```xml
<!-- In the persistence module pom.xml -->
<plugin>
    <groupId>org.liquibase</groupId>
    <artifactId>liquibase-maven-plugin</artifactId>
    <version>${liquibase-maven-plugin.version}</version>
    <configuration>
        <skip>false</skip>
        <searchPath>${project.basedir}/src/main/liquibase</searchPath>
        <propertyFile>liquibase-offline.properties</propertyFile>
        <changeLogFile>db.changelog-master.xml</changeLogFile>
        <outputDirectory>${project.build.directory}/liquibase</outputDirectory>
        <migrationSqlOutputFile>${project.build.directory}/liquibase/migration.sql</migrationSqlOutputFile>
    </configuration>
    <executions>
        <execution>
            <id>generate-migration-sql</id>
            <phase>prepare-package</phase>
            <goals>
                <goal>updateSQL</goal>
            </goals>
        </execution>
    </executions>
    <dependencies>
        <dependency>
            <groupId>org.postgresql</groupId>
            <artifactId>postgresql</artifactId>
            <version>${postgresql.version}</version>
        </dependency>
    </dependencies>
</plugin>
```

### liquibase-offline.properties

```properties
# Configuration for offline SQL generation (no live database required)
driver=org.postgresql.Driver
url=offline:postgresql?version=16&changeLogFile=${project.basedir}/src/main/liquibase/db.changelog-master.xml
username=catalog
password=catalog
outputDefaultSchema=false
```

The SQL generated at `target/liquibase/migration.sql` can be mounted in Docker Compose:

```yaml
postgres:
  image: postgres:16-alpine
  volumes:
    - ./target/liquibase/migration.sql:/docker-entrypoint-initdb.d/migration.sql
```

---

## Tests with Liquibase + Testcontainers

```java
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@Testcontainers
class ProductRepositoryIT {

    @Container
    @ServiceConnection
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine");

    @Autowired
    ProductJpaRepository repository;

    @Test
    void findByStatus_returnsActiveProducts() {
        // Liquibase ran all changelogs on Spring startup
        List<ProductJpaEntity> products = repository.findByStatus("ACTIVE");
        assertThat(products).isNotEmpty();
    }
}
```

```yaml
# src/test/resources/application-test.yaml
spring:
  liquibase:
    change-log: classpath:/liquibase/db.changelog-master.xml
    enabled: true
  jpa:
    hibernate:
      ddl-auto: validate
```

To expose changelogs on the test classpath:

```xml
<!-- pom.xml of the persistence module -->
<build>
    <testResources>
        <testResource>
            <directory>${project.basedir}/src/test/resources</directory>
        </testResource>
        <!-- Exposes changelogs to the test classpath -->
        <testResource>
            <directory>${project.basedir}/src/main/liquibase</directory>
        </testResource>
    </testResources>
</build>
```

---

## Useful CLI Commands

```bash
# Apply pending migrations
mvn liquibase:update

# Generate offline SQL (no database required)
mvn liquibase:updateSQL

# Check migration status
mvn liquibase:status

# Roll back the last changeset
mvn liquibase:rollback -Dliquibase.rollbackCount=1

# Validate changelog
mvn liquibase:validate

# Generate diff between database and changelogs
mvn liquibase:diff
```

---

## Best Practices

### DO
- One changeset per atomic operation (one table, one column)
- Always include explicit `<rollback>` blocks
- Separate DDL (schema) from DML (data) in distinct directories
- Use `labels` to categorize changesets (`ddl`, `dml`, `migration`)
- Generate offline SQL for PR review before deploying
- Use `ddl-auto: validate` in production

### DON'T
- Modify already-applied changesets — create a new one instead
- Use `ddl-auto: create` or `update` alongside Liquibase
- Use duplicate changeset IDs
- Create changesets without rollback blocks (complicates emergency rollbacks)
- Put business logic in changesets (schema and reference data only)

### Numbering Strategy

```
001-099: Initial DDL (tables, indexes, FKs)
101-199: Initial DML (reference data)
200-299: Evolutionary DDL (alterations to existing tables)
300-399: Evolutionary DML (data updates)
```

---

## Related Skills

- `spring-boot` — Spring Boot module structure and JPA configuration
- `jpa-patterns` — JPA entity design, repository patterns, and N+1 prevention
- `deployment-patterns` — Blue/green and canary deployments with schema migration coordination
- `spring-boot-testing` — Integration tests with `@DataJpaTest` and Testcontainers
