---
name: maven-dependency-audit
description: Audit Maven dependencies for outdated versions, security vulnerabilities, conflicts, and multi-module project health. Use when checking dependencies, auditing before releases, or reviewing multi-module Maven project structure.
metadata:
  version: "1.2.0"
  domain: backend
  triggers: Maven, dependencies, audit, outdated dependencies, CVE, multi-module, pom.xml, dependency conflicts
  role: reviewer
  scope: review
---

# Maven Dependency Audit Skill

Audit Maven dependencies in single and multi-module projects for updates, vulnerabilities, conflicts, and BOM consistency.

## When to Use
- "check dependencies" / "audit dependencies" / "outdated dependencies"
- Before a release
- Regular maintenance (monthly recommended)
- After security advisory
- Reviewing multi-module Maven project structure

## Audit Workflow

1. **Check for updates** - Find outdated dependencies and plugins
2. **Analyze tree** - Find conflicts, duplicates, and missing BOM entries
3. **Security scan** - Check for CVEs (OWASP)
4. **Multi-module health** - Verify BOM usage, annotation processors, module isolation
5. **Report** - Summary with prioritized actions

---

## 1. Check for Outdated Dependencies

```bash
# Outdated dependencies
mvn versions:display-dependency-updates

# Outdated plugins
mvn versions:display-plugin-updates

# Properties only (useful for BOM with centralized properties)
mvn versions:display-property-updates
```

### Categorize Updates

| Category | Criteria | Action |
|----------|----------|--------|
| **Security** | CVE fix in newer version | Update ASAP |
| **Major** | x.0.0 change | Review changelog, test thoroughly |
| **Minor** | x.y.0 change | Usually safe, test |
| **Patch** | x.y.z change | Safe, minimal testing |

---

## 2. Multi-Module Maven Structure

### BOM Pattern (Root pom.xml)

The root pom must act as a BOM (Bill of Materials) centralizing all dependency versions:

```xml
<properties>
    <!-- Centralized versions — never in submodules -->
    <java.version>25</java.version>
    <spring-boot.version>4.0.5</spring-boot.version>
    <spring-cloud.version>2025.1.1</spring-cloud.version>
    <spring-data.version>2025.1.4</spring-data.version>
    <hibernate.version>7.3.0.Final</hibernate.version>
    <liquibase-maven-plugin.version>5.0.2</liquibase-maven-plugin.version>
    <mapstruct.version>1.6.3</mapstruct.version>
    <lombok.version>1.18.44</lombok.version>
    <openapi-generator-maven-plugin.version>7.21.0</openapi-generator-maven-plugin.version>
    <protobuf-maven-plugin.version>5.0.2</protobuf-maven-plugin.version>
    <spotbugs-maven-plugin.version>4.9.8.2</spotbugs-maven-plugin.version>
    <spotless-maven-plugin.version>3.3.0</spotless-maven-plugin.version>
    <dependency-check-maven.version>9.0.7</dependency-check-maven.version>
</properties>

<dependencyManagement>
    <dependencies>
        <!-- Spring BOMs — import before declaring dependencies -->
        <dependency>
            <groupId>org.springframework.cloud</groupId>
            <artifactId>spring-cloud-dependencies</artifactId>
            <version>${spring-cloud.version}</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
        <dependency>
            <groupId>org.springframework.data</groupId>
            <artifactId>spring-data-bom</artifactId>
            <version>${spring-data.version}</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>

        <!-- Own project modules (no hardcoded version) -->
        <dependency>
            <groupId>${project.groupId}</groupId>
            <artifactId>my-domain</artifactId>
            <version>${project.version}</version>
        </dependency>
    </dependencies>
</dependencyManagement>
```

### Annotation Processors en Compiler Plugin

Annotation processors (Lombok, MapStruct, Hibernate Metamodel) must be configured as `annotationProcessorPaths` in the compiler plugin of the root pom:

```xml
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

**Lombok + MapStruct note:** If a module uses both, add `lombok-mapstruct-binding` to guarantee the correct processing order:

```xml
<path>
    <groupId>org.projectlombok</groupId>
    <artifactId>lombok-mapstruct-binding</artifactId>
    <version>0.2.0</version>
</path>
```

### OWASP Security Check como Profile

Isolate OWASP in a Maven profile so it does not block regular builds:

```xml
<profiles>
    <profile>
        <id>owasp</id>
        <build>
            <plugins>
                <plugin>
                    <groupId>org.owasp</groupId>
                    <artifactId>dependency-check-maven</artifactId>
                    <version>${dependency-check-maven.version}</version>
                    <configuration>
                        <skipProvidedScope>true</skipProvidedScope>
                    </configuration>
                    <executions>
                        <execution>
                            <phase>test</phase>
                            <goals><goal>check</goal></goals>
                        </execution>
                    </executions>
                </plugin>
            </plugins>
        </build>
    </profile>
</profiles>
```

Ejecutar: `mvn verify -P owasp`

---

## 3. Analyze Dependency Tree

```bash
# Full dependency tree
mvn dependency:tree

# Filter specific dependency
mvn dependency:tree -Dincludes=org.slf4j

# Multi-module: tree for specific module
mvn dependency:tree -pl catalog-infrastructure/catalog-infrastructure-persistence-jpa

# Detect used-but-undeclared / declared-but-unused dependencies
mvn dependency:analyze
```

### Conflicts Detection

```
[INFO] +- com.example:module-a:jar:1.0:compile
[INFO] |  \- org.slf4j:slf4j-api:jar:1.7.36:compile
[INFO] +- com.example:module-b:jar:1.0:compile
[INFO] |  \- org.slf4j:slf4j-api:jar:2.0.9:compile (omitted for conflict)
```

- `(omitted for conflict)` → Version resolved by Maven nearest-wins; can be surprising
- Fix with `<dependencyManagement>` to force a specific version

### Dependency Exclusions

```xml
<!-- Exclude commons-logging when using SLF4J bridge -->
<dependency>
    <groupId>org.springframework</groupId>
    <artifactId>spring-core</artifactId>
    <exclusions>
        <exclusion>
            <groupId>commons-logging</groupId>
            <artifactId>commons-logging</artifactId>
        </exclusion>
    </exclusions>
</dependency>

<!-- Exclude spring-boot-starter-logging when using Log4j2 -->
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
```

---

## 4. Security Vulnerability Scan

### OWASP Dependency-Check

```bash
# Vulnerability scan (owasp profile)
mvn verify -P owasp

# Report at target/dependency-check-report.html
```

### Severity Levels

| CVSS Score | Severity | Action |
|------------|----------|--------|
| 9.0 - 10.0 | Critical | Update immediately |
| 7.0 - 8.9 | High | Update within days |
| 4.0 - 6.9 | Medium | Update within weeks |
| 0.1 - 3.9 | Low | Update at convenience |

---

## 5. Quality Tools Configuration

### Spotless (Code Formatting)

```xml
<plugin>
    <groupId>com.diffplug.spotless</groupId>
    <artifactId>spotless-maven-plugin</artifactId>
    <version>${spotless-maven-plugin.version}</version>
    <configuration>
        <java>
            <cleanthat/>
            <!-- Eclipse formatter for Java 25 (Google Java Format not yet compatible) -->
            <eclipse>
                <version>4.33</version>
            </eclipse>
            <importOrder/>
            <removeUnusedImports/>
            <formatAnnotations/>
        </java>
    </configuration>
</plugin>
```

**Note:** `google-java-format` is not yet compatible with Java 25 — use Eclipse formatter.

### SpotBugs (Static Analysis)

```xml
<plugin>
    <groupId>com.github.spotbugs</groupId>
    <artifactId>spotbugs-maven-plugin</artifactId>
    <version>${spotbugs-maven-plugin.version}</version>
    <executions>
        <execution>
            <id>check</id>
            <phase>verify</phase>
            <goals><goal>check</goal></goals>
        </execution>
    </executions>
</plugin>
```

---

## 6. Generate Audit Report

```markdown
## Dependency Audit Report

**Project:** {project-name}
**Date:** {date}
**Java:** 25 | **Spring Boot:** 4.0.x | **Modules:** N

### Security Issues

| Dependency | Current | CVE | Severity | Fixed In |
|------------|---------|-----|----------|----------|

### BOM / Multi-Module Issues

- Hardcoded versions in submodules (must be in root pom properties)
- Project module dependencies without entry in dependencyManagement
- Domain modules with framework dependencies (violates hexagonal architecture)

### Outdated Dependencies

#### Major Updates (Review Required)
| Dependency | Current | Latest | Notes |
|------------|---------|--------|-------|

#### Minor/Patch Updates (Safe)
| Dependency | Current | Latest |
|------------|---------|--------|

### Conflicts Detected
- slf4j-api: 1.7.36 vs 2.0.9 (resolved to 2.0.9)

### Recommendations
1. **Immediate:** Security fixes
2. **This sprint:** Minor/patch updates
3. **Plan:** Major version migrations
```

---

## Common Scenarios

### Check Before Release

```bash
# Quick check (multi-module)
mvn versions:display-dependency-updates -q

# Full audit
mvn versions:display-dependency-updates && \
mvn dependency:analyze && \
mvn verify -P owasp
```

### Find Why Dependency is Included

```bash
mvn dependency:tree -Dincludes=commons-logging
```

### Force Specific Version (Resolve Conflict)

```xml
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.slf4j</groupId>
            <artifactId>slf4j-api</artifactId>
            <version>2.0.9</version>
        </dependency>
    </dependencies>
</dependencyManagement>
```

### Module Isolation Check (Hexagonal)

```bash
# Verify the domain module has no Spring dependencies
mvn dependency:tree -pl my-domain | grep -i spring
# Should return nothing
```

---

## Multi-Module Quick Commands

| Task | Command |
|------|---------|
| All modules outdated deps | `mvn versions:display-dependency-updates` |
| Specific module | `mvn versions:display-dependency-updates -pl module-name` |
| Full dependency tree | `mvn dependency:tree` |
| Find specific dep | `mvn dependency:tree -Dincludes=groupId:artifactId` |
| Unused/undeclared | `mvn dependency:analyze` |
| Security scan | `mvn verify -P owasp` |
| Code format check | `mvn spotless:check` |
| Code format apply | `mvn spotless:apply` |
| SpotBugs | `mvn spotbugs:check` |

## Update Strategies

### Conservative (Recommended for Production)
1. Update patch versions freely
2. Update minor versions with basic testing
3. Major versions require migration plan

### Selective
```bash
# Update specific dependency
mvn versions:use-latest-versions -Dincludes=org.junit.jupiter
```

---

## Related Skills

- `spring-boot` — Multi-module Maven setup and BOM pattern for version centralization
- `clean-ddd-hexagonal` — Module isolation principles; domain modules must not depend on frameworks
- `observability` — SpotBugs and OWASP profiles integrate into the CI pipeline alongside metrics
- `springboot-security` — OWASP dependency-check is the first line of defense for supply chain security
- `deployment-patterns` — Audit dependencies before cutting a release branch or deploying to production
