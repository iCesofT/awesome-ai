# Patrones de detección

Este documento lista los patrones concretos (regex y heurísticas) para detectar sinks (puntos de salida) y sources (datos sensibles) en código Java. Consúltalo cuando necesites el patrón exacto para validar un hallazgo.

## Tabla de contenidos

1. [Sinks — Puntos donde los datos salen del código](#sinks)
2. [Sources — Cómo detectar datos sensibles](#sources)
3. [Patrones específicos por framework de logging](#frameworks)
4. [Heurísticas para reducir falsos positivos](#falsos-positivos)

---

## Sinks

### 1. Loggers SLF4J / Logback (el más común en Java moderno)

Regex base:
```
\b(log|logger|LOG|LOGGER)\s*\.\s*(trace|debug|info|warn|error)\s*\(
```

Variantes a detectar:
- `log.info("texto " + variable)` — concatenación con `+`
- `log.info("texto {}", variable)` — placeholder SLF4J
- `log.info("texto {} y {}", a, b)` — múltiples placeholders
- `log.info("texto", throwable)` — último parámetro es una Throwable
- `log.info(marker, "texto", ...)` — con marker
- `log.atInfo().log("...")` — API fluent SLF4J 2.x
- `log.atInfo().addKeyValue("dni", dni).log("...")` — fluent con KV

### 2. Log4j / Log4j2

```
\b(log|logger)\s*\.\s*(trace|debug|info|warn|error|fatal)\s*\(
\b(log|logger)\s*\.\s*log\s*\(\s*Level\.
```

Adicional para Log4j2:
- `logger.printf(Level.INFO, "format %s", value)`
- `ThreadContext.put("key", value)` — equivalente a MDC

### 3. java.util.logging (JUL)

```
\b(log|logger)\s*\.\s*(finest|finer|fine|config|info|warning|severe)\s*\(
\b(log|logger)\s*\.\s*log\s*\(\s*Level\.
\b(log|logger)\s*\.\s*logp\s*\(
```

### 4. System.out / System.err

```
System\s*\.\s*(out|err)\s*\.\s*(print|println|printf|format)\s*\(
```

### 5. Throwable.printStackTrace

```
\.printStackTrace\s*\(
```
Si se invoca sobre una excepción que envuelve un mensaje con datos sensibles, los datos acaban en stderr.

### 6. Mensajes de excepción con concatenación

```
throw\s+new\s+\w+(Exception|Error)\s*\(\s*"[^"]*"\s*\+
throw\s+new\s+\w+(Exception|Error)\s*\(\s*String\.format\s*\(
```

El patrón típico problemático:
```java
throw new IllegalArgumentException("IBAN inválido: " + iban);
```

### 7. MDC / ThreadContext

```
MDC\s*\.\s*put\s*\(
ThreadContext\s*\.\s*put\s*\(
org\.slf4j\.MDC\.
```

### 8. Respuestas HTTP / REST

Patrones donde los controladores Spring devuelven mensajes con datos sensibles:
```
ResponseEntity\.[a-zA-Z]+\(\)\.body\s*\(
@ExceptionHandler.*return.*\+
ResponseStatusException\s*\(\s*HttpStatus\.[A-Z_]+\s*,\s*"[^"]*"\s*\+
```

### 9. toString() — el sink silencioso

Detectar clases con campos sensibles que:
- Tienen `@Data`, `@ToString` de Lombok sin exclusiones
- Sobrescriben `toString()` manualmente incluyendo todos los campos
- Son records (Java 14+) — el `toString()` sintetizado incluye TODOS los componentes

Ejemplos peligrosos:
```java
@Data
public class Cuenta {
    private String iban;  // ⚠️ aparecerá en toString()
    private BigDecimal saldo;
}

public record Cliente(String dni, String nombre, String email) {}
// ⚠️ Cliente.toString() -> "Cliente[dni=12345678A, nombre=..., email=...]"
```

Para detectar: buscar `@Data`, `@ToString` (sin `exclude` ni `onlyExplicitlyIncluded`) y records que contengan nombres de campos sensibles según el catálogo.

### 10. Serialización Jackson/Gson en logs

```java
log.info("Objeto: {}", objectMapper.writeValueAsString(obj));
log.info("JSON: " + new Gson().toJson(obj));
```
El contenido JSON incluirá todos los campos no marcados con `@JsonIgnore` / `transient`.

### 11. Auditores y tracers personalizados

Buscar por nombre heurístico:
```
\b(audit|tracer|tracker|telemetry|monitoring|metrics)[A-Z]\w*\s*\.\s*\w+\s*\(
```

---

## Sources

Dos enfoques combinados: **por nombre** (rápido, amplio) y **por formato** (preciso, más lento).

### Por nombre de variable/campo/parámetro

Lista de nombres (case-insensitive) que sugieren dato sensible. Ordenada por categoría:

**Financieros:**
```
iban, bic, swift, accountNumber, numeroCuenta, codigoIban
cardNumber, creditCard, debitCard, pan, tarjeta, numTarjeta
cvv, cvc, cvv2, securityCode, codigoSeguridad
expirationDate, expiryDate, fechaCaducidad, validThru
```

**Identificación personal:**
```
dni, nie, nif, documento, docIdentidad, identityNumber
ssn, socialSecurity, numSeguridadSocial, nss, nuss
passport, pasaporte, passportNumber
taxId, vatNumber, rfc, curp, cpf, cnpj
driverLicense, carnetConducir, permisoConducir
```

**Credenciales:**
```
password, passwd, pwd, clave, contrasena, contrasenya
secret, apiKey, api_key, apiToken, accessToken, refreshToken
privateKey, claveSecreta, claveJwt
token, bearerToken, jwt, authToken
clientSecret, consumerSecret
```

**PII general:**
```
email, correo, correoElectronico, mail
phone, phoneNumber, telefono, movil, celular, mobile
birthDate, fechaNacimiento, dob, dateOfBirth
address, direccion, street, calle
zipCode, postalCode, codigoPostal
ip, ipAddress, clientIp
```

**Datos especiales GDPR Art. 9:**
```
healthData, datosSanitarios, diagnosis, diagnostico
bloodType, grupoSanguineo
biometric, fingerprint, huellaDactilar
religion, politicalView, orientation, ethnicity
```

### Por formato de contenido (regex sobre literales y valores)

#### IBAN (ISO 13616)
```regex
\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b
```
Validación adicional: comprobar dígito de control MOD-97. Longitud correcta por país (ES=24, FR=27, DE=22...).

#### PAN / Tarjeta de crédito
```regex
\b(?:\d[ -]?){13,19}\b
```
Validación obligatoria: **algoritmo de Luhn**. Sin Luhn hay demasiados falsos positivos. Rangos BIN conocidos:
- Visa: empieza por 4, longitud 13/16/19
- Mastercard: 51-55 o 2221-2720, longitud 16
- Amex: 34 o 37, longitud 15
- Discover: 6011/65/644-649, longitud 16

#### CVV
No tiene patrón único detectable por regex (3-4 dígitos). Detectar sólo por **nombre de variable**.

#### DNI español
```regex
\b\d{8}[A-HJ-NP-TV-Z]\b
```
Validación: letra calculada como `"TRWAGMYFPDXBNJZSQVHLCKE".charAt(numero % 23)`.

#### NIE español
```regex
\b[XYZ]\d{7}[A-HJ-NP-TV-Z]\b
```
Validación: sustituir X→0, Y→1, Z→2 y aplicar misma regla que DNI.

#### NIF empresa (CIF viejo, ahora NIF)
```regex
\b[ABCDEFGHJNPQRSUVW]\d{7}[0-9A-J]\b
```

#### Pasaporte español (heurística, no hay formato único)
```regex
\b[A-Z]{3}\d{6}\b
```

#### SSN (US)
```regex
\b\d{3}-\d{2}-\d{4}\b
\b\d{9}\b  (ambiguo — requiere contexto)
```

#### Email
```regex
\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b
```

#### Teléfono español
```regex
(?:\+34|0034|34)?[\s-]?[6789]\d{2}[\s-]?\d{3}[\s-]?\d{3}
```

#### IP v4
```regex
\b(?:\d{1,3}\.){3}\d{1,3}\b
```

#### JWT (3 segmentos base64 separados por punto)
```regex
\beyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b
```

#### API keys / tokens genéricos (alta entropía)
```regex
\b(?:sk|pk|rk|AKIA|ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{16,}\b
\b[A-Za-z0-9+/]{32,}={0,2}\b  (base64 largo — puede ser token)
```

---

## Frameworks

### Spring Boot — puntos típicos de fuga

1. `@RestControllerAdvice` con manejadores que devuelven el mensaje de excepción.
2. `application.properties` con `logging.level.root=DEBUG` y `DataSourceAutoConfiguration` logueando queries con parámetros.
3. `@Transactional` con `rollbackFor` que loguea el objeto completo.
4. Filtros HTTP que loguean `request.getHeader("Authorization")`.
5. `DefaultErrorAttributes` devolviendo trace completo en 500.

### Lombok

Anotaciones a vigilar:
- `@Data` — genera `toString()` con todos los campos
- `@ToString` sin `exclude` — igual
- `@Slf4j` — sólo añade logger, no es un sink por sí mismo
- `@Value` — genera `toString()` incluyendo todos los campos

### JPA / Hibernate

- `show_sql=true` + `format_sql=true` loguea queries con parámetros.
- `org.hibernate.SQL=DEBUG` y `org.hibernate.type.descriptor.sql.BasicBinder=TRACE` loguean los valores `?` sustituidos.
- `@Entity` + `toString()` autogenerado por IDE es el mismo problema que con Lombok.

### Spring Security

- `DEBUG` en `org.springframework.security` puede loguear tokens y detalles de autenticación.
- `UsernamePasswordAuthenticationToken.toString()` en versiones antiguas incluía la contraseña hasta borrarse.

---

## Falsos positivos

Patrones frecuentes que parecen hallazgos pero no lo son. Menciona la sospecha en el informe pero marca como "posible FP":

1. **Tests unitarios**: `"4111111111111111"` es el PAN de prueba universal de Visa. No es una fuga real, pero sí conviene no loguearlo en INFO de tests que vayan a CI con logs públicos.
2. **Datos sintéticos en documentación**: javadoc con ejemplos de IBAN.
3. **Constantes de validación**: `private static final String IBAN_REGEX = "..."`.
4. **Mappers que sólo renombran**: `dto.setIban(entity.getIban())` no loguea nada por sí solo.
5. **Variables con nombre engañoso**: `passwordPolicy`, `tokenExpirationDays`, `secretQuestionId` — son config, no el secreto en sí.
6. **Logs enmascarados ya**: si ves `log.info("IBAN: {}", mask(iban))` está OK; identifica `mask`, `masked`, `obfuscate`, `redact`, `sanitize`, `anonymize` como funciones probablemente seguras.

Regla práctica: si en la misma línea o 1-2 líneas arriba hay una llamada a una función cuyo nombre contiene `mask|obfuscate|redact|sanitize|anonymize|hash|encrypt`, probablemente es FP.
