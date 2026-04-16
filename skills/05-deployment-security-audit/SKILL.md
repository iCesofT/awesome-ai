---
name: security-audit
description: Java security checklist and AI-powered code scanner covering OWASP Top 10, input validation, injection prevention, authentication/authorization, secrets management, and multi-language vulnerability detection. Use when reviewing code security, before releases, or when user asks about vulnerabilities.
metadata:
  version: "1.1.0"
  domain: backend
  triggers: security, vulnerability, OWASP, SQL injection, XSS, CSRF, authentication, authorization, secrets, CVE, security audit
  role: specialist
  scope: review
---

# Security Audit Skill

Security checklist and AI-powered scanner for Java applications based on OWASP Top 10 and secure coding practices. Covers multi-language vulnerability patterns including JS, Python, Go, Rust.

## When to Use
- Security code review or scanning a codebase
- Before production releases
- User asks about "security", "vulnerability", "OWASP"
- Reviewing authentication/authorization code
- Checking for injection vulnerabilities
- Finding exposed API keys, hardcoded secrets
- Auditing dependencies for known CVEs

---

## Security Scan Workflow

When performing a security review, follow these steps **in order**:

1. **Scope Resolution** — Determine languages and frameworks (check pom.xml, package.json, etc.)
2. **Dependency Audit** — Scan for known CVEs and vulnerable packages first (fast wins)
3. **Secrets & Exposure Scan** — Find hardcoded credentials, API keys, .env files committed
4. **Vulnerability Deep Scan** — Trace data flows, injection flaws, auth/authz issues
5. **Cross-File Data Flow** — Follow user input from entry points to dangerous sinks
6. **Self-Verification** — Re-examine findings to filter false positives
7. **Report** — Severity ratings (CRITICAL/HIGH/MEDIUM/LOW/INFO) + concrete fix per finding

---

## OWASP Top 10 Quick Reference

| # | Risk | Java Mitigation |
|---|------|-----------------|
| A01 | Broken Access Control | Role-based checks, deny by default |
| A02 | Cryptographic Failures | Use strong algorithms, no hardcoded secrets |
| A03 | Injection | Parameterized queries, input validation |
| A04 | Insecure Design | Threat modeling, secure defaults |
| A05 | Security Misconfiguration | Disable debug, secure headers |
| A06 | Vulnerable Components | Dependency scanning, updates |
| A07 | Authentication Failures | Strong passwords, MFA, session management |
| A08 | Data Integrity Failures | Verify signatures, secure deserialization |
| A09 | Logging Failures | Log security events, no sensitive data |
| A10 | SSRF | Validate URLs, allowlist domains |

---

## Input Validation (All Frameworks)

### Bean Validation (JSR 380)

```java
// ✅ GOOD: Validate at boundary
public class CreateUserRequest {

    @NotNull(message = "Username is required")
    @Size(min = 3, max = 50, message = "Username must be 3-50 characters")
    @Pattern(regexp = "^[a-zA-Z0-9_]+$", message = "Username can only contain letters, numbers, underscore")
    private String username;

    @NotNull
    @Email(message = "Invalid email format")
    private String email;

    @NotNull
    @Size(min = 8, max = 100)
    @Pattern(regexp = "^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d).*$",
             message = "Password must contain uppercase, lowercase, and number")
    private String password;

    @Min(value = 0, message = "Age cannot be negative")
    @Max(value = 150, message = "Invalid age")
    private Integer age;
}

// Controller/Resource - trigger validation
public Response createUser(@Valid CreateUserRequest request) {
    // request is already validated
}
```

### Custom Validators

```java
// Custom annotation
@Target({ElementType.FIELD})
@Retention(RetentionPolicy.RUNTIME)
@Constraint(validatedBy = SafeHtmlValidator.class)
public @interface SafeHtml {
    String message() default "Contains unsafe HTML";
    Class<?>[] groups() default {};
    Class<? extends Payload>[] payload() default {};
}

// Validator implementation
public class SafeHtmlValidator implements ConstraintValidator<SafeHtml, String> {

    private static final Pattern DANGEROUS_PATTERN = Pattern.compile(
        "<script|javascript:|on\\w+\\s*=", Pattern.CASE_INSENSITIVE
    );

    @Override
    public boolean isValid(String value, ConstraintValidatorContext context) {
        if (value == null) return true;
        return !DANGEROUS_PATTERN.matcher(value).find();
    }
}
```

### Allowlist vs Blocklist

```java
// ❌ BAD: Blocklist (attackers find bypasses)
if (input.contains("<script>")) {
    throw new ValidationException("Invalid input");
}

// ✅ GOOD: Allowlist (only permit known-good)
private static final Pattern SAFE_NAME = Pattern.compile("^[a-zA-Z\\s'-]{1,100}$");

if (!SAFE_NAME.matcher(input).matches()) {
    throw new ValidationException("Invalid name format");
}
```

---

## SQL Injection Prevention

### JPA/Hibernate

```java
// ✅ GOOD: Parameterized queries
@Query("SELECT u FROM User u WHERE u.email = :email")
Optional<User> findByEmail(@Param("email") String email);

// ✅ GOOD: Named parameters
TypedQuery<User> query = entityManager.createQuery(
    "SELECT u FROM User u WHERE u.status = :status", User.class);
query.setParameter("status", status);  // Safe

// ❌ BAD: String concatenation
String jpql = "SELECT u FROM User u WHERE u.email = '" + email + "'";  // VULNERABLE!
```

### JDBC (Plain Java)

```java
// ✅ GOOD: PreparedStatement
String sql = "SELECT * FROM users WHERE email = ? AND status = ?";
try (PreparedStatement stmt = connection.prepareStatement(sql)) {
    stmt.setString(1, email);
    stmt.setString(2, status);
    ResultSet rs = stmt.executeQuery();
}

// ❌ BAD: Statement with concatenation
String sql = "SELECT * FROM users WHERE email = '" + email + "'";  // VULNERABLE!
Statement stmt = connection.createStatement();
stmt.executeQuery(sql);
```

---

## XSS Prevention

### Output Encoding

```java
// Thymeleaf - auto-escapes by default
<p th:text="${userInput}">...</p>  // Safe
<p th:utext="${trustedHtml}">...</p>  // Only for trusted content!

// ✅ GOOD: Manual encoding when needed
import org.owasp.encoder.Encode;
String safe = Encode.forHtml(userInput);
String safeJs = Encode.forJavaScript(userInput);
String safeUrl = Encode.forUriComponent(userInput);
```

```xml
<dependency>
    <groupId>org.owasp.encoder</groupId>
    <artifactId>encoder</artifactId>
    <version>1.2.3</version>
</dependency>
```

### Content Security Policy

```java
@Bean
public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
    http.headers(headers -> headers
        .contentSecurityPolicy(csp -> csp
            .policyDirectives("default-src 'self'; script-src 'self'; style-src 'self'")
        )
    );
    return http.build();
}
```

---

## CSRF Protection

```java
// For REST APIs with JWT (stateless) - can disable CSRF
.csrf(csrf -> csrf.disable())

// For browser apps with sessions - keep CSRF enabled
.csrf(csrf -> csrf
    .csrfTokenRepository(CookieCsrfTokenRepository.withHttpOnlyFalse())
);
```

---

## Authentication & Authorization

### Password Storage

```java
// ✅ GOOD: Use BCrypt or Argon2
// BCrypt (widely supported)
PasswordEncoder encoder = new BCryptPasswordEncoder(12);  // strength 12
String hash = encoder.encode(rawPassword);
boolean matches = encoder.matches(rawPassword, hash);

// Argon2 (recommended for new projects)
PasswordEncoder encoder = Argon2PasswordEncoder.defaultsForSpringSecurity_v5_8();
String hash = encoder.encode(rawPassword);

// ❌ BAD: MD5, SHA1, SHA256 without salt
String hash = DigestUtils.md5Hex(password);  // NEVER for passwords!
```

### Authorization Checks

```java
// ✅ GOOD: Check authorization at service layer
@Service
public class DocumentService {

    public Document getDocument(Long documentId, User currentUser) {
        Document doc = documentRepository.findById(documentId)
            .orElseThrow(() -> new NotFoundException("Document not found"));

        // Authorization check
        if (!doc.getOwnerId().equals(currentUser.getId()) &&
            !currentUser.hasRole("ADMIN")) {
            throw new AccessDeniedException("Not authorized to access this document");
        }

        return doc;
    }
}

// ❌ BAD: Only check at controller level, trust user input
@GetMapping("/documents/{id}")
public Document getDocument(@PathVariable Long id) {
    return documentRepository.findById(id).orElseThrow();  // No auth check!
}
```

### Spring Security Method Annotations

```java
@PreAuthorize("hasRole('ADMIN')")
public void adminOnly() { }

@PreAuthorize("hasRole('USER') and #userId == authentication.principal.id")
public void ownDataOnly(Long userId) { }

@PreAuthorize("@authService.canAccess(#documentId, authentication)")
public Document getDocument(Long documentId) { }
```

---

## Secrets Management

```java
// ❌ BAD: Hardcoded secrets
private static final String API_KEY = "sk-1234567890abcdef";
private static final String DB_PASSWORD = "admin123";

// ✅ GOOD: Environment variables
String apiKey = System.getenv("API_KEY");

// ✅ GOOD: @Value from application.yaml
@Value("${api.key}")
private String apiKey;

// ✅ GOOD: Secrets manager (Vault, AWS Secrets Manager, etc.)
@Autowired
private SecretsManager secretsManager;
String apiKey = secretsManager.getSecret("api-key");
```

```yaml
# ✅ GOOD: Reference environment variables
spring:
  datasource:
    password: ${DB_PASSWORD}

# ❌ BAD: Hardcoded in application.yml
spring:
  datasource:
    password: admin123  # NEVER!
```

```gitignore
# .gitignore — Never commit these
.env
*.pem
*.key
*credentials*
*secret*
application-local.yml
```

---

## Secure Deserialization

```java
// ❌ DANGEROUS: Java ObjectInputStream
ObjectInputStream ois = new ObjectInputStream(untrustedInput);
Object obj = ois.readObject();  // Remote Code Execution risk!

// ✅ GOOD: Use JSON with Jackson (safely configured)
@Configuration
public class JacksonConfig {

    @Bean
    public ObjectMapper objectMapper() {
        ObjectMapper mapper = new ObjectMapper();

        // Prevent unknown properties exploitation
        mapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);

        // Don't allow class type in JSON (prevents gadget attacks)
        mapper.deactivateDefaultTyping();

        return mapper;
    }
}
```

---

## Dependency Security

### OWASP Dependency Check

```xml
<plugin>
    <groupId>org.owasp</groupId>
    <artifactId>dependency-check-maven</artifactId>
    <version>9.0.7</version>
    <executions>
        <execution>
            <goals>
                <goal>check</goal>
            </goals>
        </execution>
    </executions>
    <configuration>
        <failBuildOnCVSS>7</failBuildOnCVSS>  <!-- Fail on high severity -->
    </configuration>
</plugin>
```

```bash
# Run check
mvn dependency-check:check
# Report: target/dependency-check-report.html

# Check for updates
mvn versions:display-dependency-updates
```

---

## Security Headers

| Header | Value | Purpose |
|--------|-------|---------|
| `Content-Security-Policy` | `default-src 'self'` | Prevent XSS |
| `X-Content-Type-Options` | `nosniff` | Prevent MIME sniffing |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `Strict-Transport-Security` | `max-age=31536000` | Force HTTPS |
| `X-XSS-Protection` | `1; mode=block` | Legacy XSS filter |

```java
@Bean
public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
    http.headers(headers -> headers
        .contentSecurityPolicy(csp -> csp.policyDirectives("default-src 'self'"))
        .frameOptions(frame -> frame.deny())
        .httpStrictTransportSecurity(hsts -> hsts.maxAgeInSeconds(31536000))
        .contentTypeOptions(Customizer.withDefaults())
    );
    return http.build();
}
```

---

## Vulnerability Categories (Multi-Language)

### Injection Flaws
- **SQL Injection**: raw queries with string interpolation, ORM misuse, second-order SQLi
- **XSS**: unescaped output, `dangerouslySetInnerHTML`, `innerHTML`, template injection
- **Command Injection**: `exec`/`spawn`/`system` with user input
- **LDAP, XPath, Header, Log injection**: any unvalidated user input in structured queries

### Authentication & Access Control
- Missing authentication on sensitive endpoints
- Broken token validation (JWT: `alg: none`, weak secret, no expiry check)
- Insecure direct object references (IDOR) — accessing resources without ownership check
- Privilege escalation through mass assignment

### Data Handling
- Sensitive data logged (passwords, tokens, PII, credit cards)
- Sensitive data returned in API responses unnecessarily
- Unencrypted sensitive data at rest or in transit
- PII in URLs (query params get logged)

### Cryptography
- Weak algorithms: MD5, SHA1, DES, RC4 for security purposes
- Hardcoded encryption keys or IVs
- Non-random IVs for AES-CBC
- Predictable random number generation (`Math.random()` for security tokens)

### Business Logic
- Missing rate limiting on sensitive endpoints (login, password reset, OTP)
- Insecure direct object reference (IDOR)
- Race conditions in financial transactions
- Batch operation abuse

---

## Logging Security Events

```java
// ✅ Log security-relevant events
log.info("User login successful", kv("userId", userId), kv("ip", clientIp));
log.warn("Failed login attempt", kv("username", username), kv("ip", clientIp), kv("attempt", attemptCount));
log.warn("Access denied", kv("userId", userId), kv("resource", resourceId), kv("action", action));
log.error("Authentication failure", kv("reason", reason), kv("ip", clientIp));

// ❌ NEVER log sensitive data
log.info("Login: user={}, password={}", username, password);  // NEVER!
log.debug("Request body: {}", requestWithCreditCard);  // NEVER!
```

---

## Security Checklists

### Code Review

- [ ] Input validated with allowlist patterns
- [ ] SQL queries use parameters (no concatenation)
- [ ] Output encoded for context (HTML, JS, URL)
- [ ] Authorization checked at service layer (not just controller)
- [ ] No hardcoded secrets (use env vars or secrets manager)
- [ ] Passwords hashed with BCrypt/Argon2
- [ ] Sensitive data not logged
- [ ] CSRF protection enabled (for browser apps)
- [ ] No Java ObjectInputStream deserialization of untrusted input

### Configuration

- [ ] HTTPS enforced
- [ ] Security headers configured (CSP, HSTS, X-Frame-Options)
- [ ] Debug/dev features disabled in production
- [ ] Default credentials changed
- [ ] Error messages don't leak internal details (stack traces, table names)
- [ ] `spring.security.debug=false` in production

### Dependencies

- [ ] No known vulnerabilities (OWASP check)
- [ ] Dependencies up to date
- [ ] Unnecessary dependencies removed
- [ ] No `.env` or credential files committed to git

---

## Related Skills

- `springboot-security` — Spring Security 6 configuration is the primary subject of a Spring Boot security audit
- `maven-dependency-audit` — OWASP dependency-check is a mandatory part of the security audit
- `gdpr-compliant` — GDPR compliance audit overlaps with security audit on data handling and access control
- `observability` — Security event logging and audit trails require proper observability infrastructure
- `deployment-patterns` — Infrastructure security (network policies, secrets management) is reviewed during deployment audits
