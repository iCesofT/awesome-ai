# Patrones de remediación

Snippets listos para usar en los hallazgos. Organizados por tipo de problema y framework.

## Tabla de contenidos

1. [Utilidades de enmascarado](#utilidades-de-enmascarado)
2. [Lombok — ToString seguro](#lombok)
3. [Jackson — Serialización JSON sin PII](#jackson)
4. [Logback — Filtros y pattern layouts](#logback)
5. [Log4j2 — RewriteAppenders y replacements](#log4j2)
6. [Spring Boot — Error handling sin fugas](#spring-boot)
7. [JPA/Hibernate — Queries sin parámetros visibles](#jpahibernate)
8. [MDC seguro](#mdc)

---

## Utilidades de enmascarado

Una clase utilitaria que conviene tener centralizada y reutilizable:

```java
public final class SensitiveDataMask {

    private SensitiveDataMask() {}

    /** ES9121000418450200051332 -> ES** **** **** **** **** 1332 */
    public static String maskIban(String iban) {
        if (iban == null || iban.length() < 8) return "***";
        String clean = iban.replaceAll("\\s", "");
        return clean.substring(0, 2) + "**...**" + clean.substring(clean.length() - 4);
    }

    /** 4539148803436467 -> 453914******6467 (PCI-DSS: BIN + últimos 4) */
    public static String maskPan(String pan) {
        if (pan == null) return "***";
        String clean = pan.replaceAll("[\\s-]", "");
        if (clean.length() < 10) return "***";
        return clean.substring(0, 6) + "*".repeat(clean.length() - 10) + clean.substring(clean.length() - 4);
    }

    /** 12345678A -> ***5678A */
    public static String maskDni(String dni) {
        if (dni == null || dni.length() < 4) return "***";
        return "*****" + dni.substring(dni.length() - 4);
    }

    /** juan.perez@example.com -> j***@example.com */
    public static String maskEmail(String email) {
        if (email == null) return "***";
        int at = email.indexOf('@');
        if (at <= 1) return "***" + email.substring(Math.max(0, at));
        return email.charAt(0) + "***" + email.substring(at);
    }

    /** Nunca loguear CVV, contraseñas ni claves — sólo devolver placeholder */
    public static String redact() {
        return "[REDACTED]";
    }
}
```

## Lombok

Exclusión selectiva de campos sensibles en `toString()`:

```java
// Opción 1: exclude (legacy, aún válido)
@Data
@ToString(exclude = {"iban", "dni", "password"})
public class Customer {
    private Long id;
    private String name;
    private String iban;
    private String dni;
    private String password;
}

// Opción 2: onlyExplicitlyIncluded + @ToString.Include por campo (más explícito)
@Data
@ToString(onlyExplicitlyIncluded = true)
public class Customer {
    @ToString.Include private Long id;
    @ToString.Include private String name;
    private String iban;      // no aparece en toString()
    private String dni;       // no aparece en toString()
    private String password;  // no aparece en toString()
}

// Opción 3: con @ToString.Exclude por campo
@Data
public class Customer {
    private Long id;
    private String name;
    @ToString.Exclude private String iban;
    @ToString.Exclude private String dni;
    @ToString.Exclude private String password;
}
```

Para records de Java 14+, Lombok no aplica. Hay que sobrescribir `toString()` manualmente:

```java
public record Customer(Long id, String name, String iban, String dni) {
    @Override
    public String toString() {
        return "Customer[id=%d, name=%s, iban=%s, dni=%s]"
            .formatted(id, name,
                SensitiveDataMask.maskIban(iban),
                SensitiveDataMask.maskDni(dni));
    }
}
```

## Jackson

Evitar que campos sensibles se serialicen en respuestas JSON:

```java
public class Customer {
    private Long id;
    private String name;

    @JsonIgnore
    private String iban;

    @JsonIgnore
    private String password;
}
```

Alternativa con vistas (útil si algunos endpoints sí pueden devolverlo):

```java
public class Views {
    public interface Public {}
    public interface Internal extends Public {}
}

public class Customer {
    @JsonView(Views.Public.class)
    private Long id;

    @JsonView(Views.Internal.class)
    private String iban;
}

// En el controller:
@JsonView(Views.Public.class)
public Customer getPublic(...) { ... }
```

Serializer personalizado que enmascara automáticamente:

```java
public class IbanMaskingSerializer extends JsonSerializer<String> {
    @Override
    public void serialize(String value, JsonGenerator gen, SerializerProvider sp) throws IOException {
        gen.writeString(SensitiveDataMask.maskIban(value));
    }
}

public class Customer {
    @JsonSerialize(using = IbanMaskingSerializer.class)
    private String iban;
}
```

## Logback

Filtro que elimina patrones sensibles del log completo. Añadir al `logback-spring.xml`:

```xml
<configuration>
    <appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
        <encoder class="ch.qos.logback.core.encoder.LayoutWrappingEncoder">
            <layout class="ch.qos.logback.classic.PatternLayout">
                <pattern>%d %-5level %logger - %replace(%replace(%msg){'\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b', '[IBAN]'}){'\b\d{8}[A-HJ-NP-TV-Z]\b', '[DNI]'}%n</pattern>
            </layout>
        </encoder>
    </appender>
</configuration>
```

Mejor todavía: un `CompositeConverter` personalizado:

```java
public class MaskingConverter extends CompositeConverter<ILoggingEvent> {
    private static final Pattern IBAN = Pattern.compile("\\b[A-Z]{2}\\d{2}[A-Z0-9]{11,30}\\b");
    private static final Pattern DNI = Pattern.compile("\\b\\d{8}[A-HJ-NP-TV-Z]\\b");
    private static final Pattern PAN = Pattern.compile("\\b(?:\\d[ -]?){13,19}\\b");

    @Override
    protected String transform(ILoggingEvent event, String in) {
        String out = IBAN.matcher(in).replaceAll("[IBAN_REDACTED]");
        out = DNI.matcher(out).replaceAll("[DNI_REDACTED]");
        out = PAN.matcher(out).replaceAll("[PAN_REDACTED]");
        return out;
    }
}
```

Registrar en `logback-spring.xml`:
```xml
<conversionRule conversionWord="maskedMsg" converterClass="com.example.MaskingConverter"/>

<pattern>%d %-5level %logger - %maskedMsg(%msg)%n</pattern>
```

**Aviso**: los filtros globales son la última línea de defensa, **no** la primera. Son costosos (regex en cada log), pueden dar falsos positivos que rompen mensajes válidos, y dan una falsa sensación de seguridad. Arregla el código primero, usa el filtro como red de seguridad.

## Log4j2

Usar un `RewritePolicy`:

```xml
<Configuration>
    <Appenders>
        <Rewrite name="Masked">
            <AppenderRef ref="Console"/>
            <PropertiesRewritePolicy>
                <Property name="iban">[IBAN_REDACTED]</Property>
            </PropertiesRewritePolicy>
        </Rewrite>
    </Appenders>
</Configuration>
```

O un `RegexReplacement` en el pattern:

```xml
<PatternLayout>
    <Pattern>%d %-5p %c{1} - %replace{%m}{\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b}{[IBAN]}%n</Pattern>
</PatternLayout>
```

## Spring Boot

`@RestControllerAdvice` que **no** filtra el mensaje de excepción crudo:

```java
@RestControllerAdvice
public class GlobalExceptionHandler {

    // MAL: devuelve ex.getMessage() que puede contener el IBAN
    @ExceptionHandler(PaymentException.class)
    public ResponseEntity<String> handlePaymentBad(PaymentException ex) {
        return ResponseEntity.badRequest().body(ex.getMessage());
    }

    // BIEN: devuelve un mensaje genérico + id de correlación
    @ExceptionHandler(PaymentException.class)
    public ResponseEntity<ErrorResponse> handlePaymentGood(PaymentException ex) {
        String correlationId = UUID.randomUUID().toString();
        log.error("Fallo de pago [{}]", correlationId, ex);  // internamente sí se logea
        return ResponseEntity.badRequest().body(
            new ErrorResponse("PAYMENT_FAILED", "No se pudo procesar el pago", correlationId)
        );
    }
}
```

Desactivar el stack trace en respuestas 500 (`application.properties`):

```properties
server.error.include-message=never
server.error.include-stacktrace=never
server.error.include-exception=false
server.error.include-binding-errors=never
```

## JPA/Hibernate

No activar jamás en producción:

```properties
# ❌ PROHIBIDO EN PROD — loguea parámetros con datos reales
spring.jpa.show-sql=true
logging.level.org.hibernate.SQL=DEBUG
logging.level.org.hibernate.type.descriptor.sql.BasicBinder=TRACE
logging.level.org.hibernate.orm.jdbc.bind=TRACE
```

Alternativa para desarrollo con sanitización: usar [P6Spy](https://github.com/p6spy/p6spy) con un `MessageFormattingStrategy` personalizado que enmascare.

## MDC

El MDC acaba en **cada línea de log** del hilo actual. Las reglas:

```java
// ❌ MAL
MDC.put("userDni", dni);
MDC.put("userEmail", email);
MDC.put("authToken", token);

// ✅ BIEN — identificadores opacos, no PII
MDC.put("userId", userUuid.toString());
MDC.put("traceId", traceId);
MDC.put("requestId", requestId);

// Siempre limpiar al final del request (filtro o interceptor)
try {
    MDC.put("traceId", traceId);
    chain.doFilter(req, res);
} finally {
    MDC.clear();
}
```

---

## Anti-patrones que se repiten

Estos patrones aparecen una y otra vez. Al encontrarlos, copia y pega la corrección:

### 1. "Log the entire object for debugging"

```java
// ❌
log.debug("Procesando cliente: {}", customer);  // toString() incluye iban, dni...

// ✅
log.debug("Procesando cliente id={} tipo={}", customer.getId(), customer.getType());
```

### 2. "Exception message with the offending value"

```java
// ❌
throw new ValidationException("IBAN inválido: " + iban);

// ✅
throw new ValidationException("IBAN inválido (longitud=" + (iban == null ? 0 : iban.length()) + ")");
```

### 3. "Log the request/response for audit"

```java
// ❌
log.info("Request recibido: {}", new ObjectMapper().writeValueAsString(request));

// ✅ Usa un ObjectMapper con MixIns que ignoren campos sensibles
private static final ObjectMapper AUDIT_MAPPER = new ObjectMapper()
    .addMixIn(PaymentRequest.class, PaymentRequestAuditView.class);

log.info("Request recibido: {}", AUDIT_MAPPER.writeValueAsString(request));
```

### 4. "System.out en producción"

```java
// ❌
System.out.println("Error procesando " + user);

// ✅
log.error("Error procesando user={}", user.getId(), exception);
```

### 5. "printStackTrace"

```java
// ❌
} catch (Exception e) {
    e.printStackTrace();
}

// ✅
} catch (Exception e) {
    log.error("Fallo en operación X", e);
    // O, si es recuperable:
    log.warn("Fallo recuperable: {}", e.getMessage());
}
```
