---
name: java-sensitive-log-auditor
description: Audit Java code for logs, exception messages, and console output that may leak sensitive data such as IBAN, PAN (credit cards), DNI/NIE/NIF, passports, credentials, tokens, API keys, emails, phone numbers, and other personal or regulated data (GDPR/PCI-DSS). Use it whenever the user mentions reviewing, auditing, or analyzing Java code for information leaks, log leaks, GDPR/PCI compliance, "sensitive data in logs", secure logging, personal data in traces, or when sharing .java files and asking to review them for data security. Also activate it when asked to review toString(), exception messages, or stack traces in Java for possible sensitive data, even if the user doesn't explicitly use the word "audit".
---

# Java Sensitive Log Auditor

Skill to detect sensitive data leaks in logs and traces of Java code. It focuses on finding patterns where information protected by GDPR, PCI-DSS, or other regulations ends up written in logs, exception messages, or console output.

## When to use this skill

Activate when the user:
- Shares Java code (`.java` files, snippets, projects) and asks to review it for data security.
- Mentions keywords such as: "sensitive logs", "information leak", "GDPR in logs", "PCI", "data leak", "IBAN in traces", "DNI in logs", "review logging".
- Asks for help with "secure logging" or "log sanitization".
- Reports an audit incident related to traces.

## Analysis Philosophy

The goal is not only to detect calls to `log.xxx(...)`, but to understand the **flow of sensitive data to any observable output channel**. A log is the obvious case, but you also need to watch for:

1. **Explicit loggers** — SLF4J, Log4j, Log4j2, JUL, Logback, Commons Logging, Tinylog.
2. **Console output** — `System.out`, `System.err`, `printStackTrace()`.
3. **`toString()` from DTOs/Entities** — Lombok `@ToString`, `@Data`, records, IDE auto-generated. If an entity with an `iban` field is logged as `"Account: " + account`, the `toString()` exposes everything.
4. **Exception messages** — `throw new RuntimeException("Error processing IBAN " + iban)`.
5. **MDC / ThreadContext** — `MDC.put("dni", dni)` ends up in every log line.
6. **Serialization in HTTP error responses** — `ResponseEntity.badRequest().body("User " + email + " not found")`.
7. **Custom audit traces** — `auditService.log(...)`, `tracer.info(...)`.

## Workflow

Follow this order when asked to perform an audit:

### 1. Inventory the code to review

- If the user provides files, list them and confirm the scope.
- If it's a large project, offer two modes:
  - **Quick mode**: targeted grep with the `scripts/scan_logs.py` script (see below).
  - **Exhaustive mode**: line-by-line review per file.
- Always ask if there are entities/DTOs with known sensitive data that you should treat as "tainted" classes.

### 2. Detect exit points (sinks)

Look for these patterns. The detailed list with regex and examples is in `references/detection_patterns.md` — consult it when you need specific patterns.

Summary of main sinks:
- `log.trace|debug|info|warn|error|fatal(...)` and variants
- `logger.log(Level.X, ...)`
- `System.out.print*`, `System.err.print*`
- `e.printStackTrace()`
- `throw new XxxException("..." + variable)`
- `MDC.put(...)`, `ThreadContext.put(...)`
- `@ToString` without `exclude`/`of` on classes with sensitive fields

### 3. Identify sensitive data (sources)

Consult `references/sensitive_data_catalog.md` for the complete catalog with regex and validations. Key categories:

| Category | Examples | Risk |
|---|---|---|
| Financial | IBAN, PAN, CVV, SWIFT/BIC, card expiration | PCI-DSS, GDPR |
| Identification (ES/EU) | DNI, NIE, NIF, passport, SS number | GDPR (Art. 9 if healthcare) |
| Identification (other) | SSN (US), CURP (MX), CPF (BR) | Local regulation |
| Credentials | password, secret, token, apiKey, privateKey, JWT | Critical always |
| General PII | email, phone, postal address, IP, date of birth | GDPR |
| Special data | health, religion, orientation, biometrics, children | GDPR Art. 9 — maximum severity |

Two types of detection:
- **By variable/field/parameter name**: `iban`, `dni`, `cardNumber`, `password`, `ssn`, `email`, `phoneNumber`, etc.
- **By literal content**: strings that match the format (e.g. `"ES9121000418450200051332"` hardcoded).

### 4. Analyze each finding and classify it

For each match, fill in these fields mentally before writing it in the report:

- **File and line**
- **Snippet** (3-5 lines of context)
- **Sink** (type of output)
- **Sensitive data** (what is leaking and why you think so)
- **Severity**:
  - 🔴 **CRITICAL**: Full PAN, CVV, passwords, private keys, active tokens, health data.
  - 🟠 **HIGH**: IBAN, complete DNI/NIE/SSN, passport, email+other combined data.
  - 🟡 **MEDIUM**: Isolated email, phone, IP, full name, date of birth.
  - 🔵 **LOW**: Internal identifiers, numeric IDs that could be correlated.
- **Confidence**: High / Medium / Low (if deduction by variable name, lower confidence).
- **Compliance affected**: PCI-DSS, GDPR, HIPAA, etc.
- **Recommendation** with proposed diff.

### 5. Produce the report

Use the template in `assets/report_template.md`. The report has three parts:

1. **Executive summary**: table of severities (how many 🔴, 🟠, 🟡, 🔵), % affected files.
2. **Detailed findings**: one per issue, sorted by severity.
3. **Cross-cutting recommendations**: patterns that repeat and deserve global refactoring (e.g. "add `@ToString(exclude={"iban","dni"})` to all entities in package `domain.*`").

### 6. Propose corrections

For each 🔴 and 🟠 finding, include a unified diff with the correction. Typical patterns:

**IBAN masking:**
```java
// BEFORE
log.info("Customer account: {}", iban);

// AFTER
log.info("Customer account: {}", MaskUtils.maskIban(iban));
// where maskIban("ES9121000418450200051332") -> "ES**...**1332"
```

**PAN according to PCI-DSS (only first 6 and last 4 if needed):**
```java
// BEFORE
log.debug("Processing card {}", cardNumber);

// AFTER
log.debug("Processing card {}", MaskUtils.maskPan(cardNumber));
// 4539148803436467 -> 453914******6467
```

**Safe Lombok ToString:**
```java
// BEFORE
@Data
public class Customer {
    private String iban;
    private String dni;
    private String email;
}

// AFTER
@Data
@ToString(exclude = {"iban", "dni"})
public class Customer {
    private String iban;
    private String dni;
    private String email; // consider also hiding or masking
}
```

**Exceptions without sensitive data:**
```java
// BEFORE
throw new PaymentException("Could not process IBAN " + iban);

// AFTER
throw new PaymentException("Could not process account (id=" + accountId + ")");
```

**Clean MDC:**
```java
// BEFORE
MDC.put("user_dni", dni);

// AFTER
MDC.put("user_id", userUuid); // internal non-PII identifier
```

In `references/remediation_patterns.md` there are more patterns (Spring Boot, Jackson `@JsonIgnore`, Logback filters, Log4j2 `RewriteAppender`, etc.).

## Auxiliary script: scan_logs.py

For large projects, use the `scripts/scan_logs.py` script as a first pass. It does semantic grep with pre-compiled regex and returns JSON with candidate findings. Then you review them one by one with your judgment.

```bash
python3 scripts/scan_logs.py <project_path> [--output findings.json]
```

**Important**: the script is an **aid**, not a substitute for analysis. False positives are common (e.g. a variable called `password` that is actually a policy, not a value). Your job is to filter, contextualize, and add findings that the regex doesn't catch (e.g. an implicit `toString()`).

## Important rules

- **Don't show actual sensitive data in the report**. If you find `"ES9121000418450200051332"` hardcoded, report it as `"ES**...**1332"` or `"<hardcoded IBAN found>"`.
- **Don't invent files or lines** that you haven't seen. If analyzing by snippets, clearly indicate "according to the provided snippet".
- **Calibrated confidence**: if you only have the variable name, say "medium confidence". Don't claim that a variable called `pwd` is a password if it could be something else.
- **Prioritize real risk**: a `log.debug` that's only active in development is less critical than a `log.error` that goes to production. Mention it.
- **Expected false positives**: tests using synthetic data (e.g. `"1234-5678-9012-3456"` as test PAN), documentation constants, examples in comments. Mark them as "possible false positive" if the context suggests it.
- **Don't hallucinate compliance**: if you're not sure which GDPR article applies, say "possible GDPR implication" instead of inventing a reference.

## What NOT to do

- Don't add lengthy legal disclaimers. A brief sentence about GDPR/PCI is enough.
- Don't rewrite the entire file if there's only one finding: show the minimal diff.
- Don't assume that because a field is called `id` it's not sensitive (a DNI might be called `customerId`).
- Don't recommend "just lower the level to TRACE": TRACE also ends up in file in many configurations.
- Don't confuse hashing with masking: a SHA-256 hash of an IBAN is still personal data under GDPR if it's reversible by dictionary.

## Reference files

- `references/detection_patterns.md` — Detailed regex and patterns by sink and source.
- `references/sensitive_data_catalog.md` — Complete catalog of sensitive data types with validations.
- `references/remediation_patterns.md` — Remediation snippets by framework (Spring, Lombok, Log4j2, Logback).
- `assets/report_template.md` — Template for the final report.
- `scripts/scan_logs.py` — First pass script.
