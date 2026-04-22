# Catálogo de datos sensibles

Referencia de los tipos de datos que esta skill considera sensibles, con su formato, validación, regulación aplicable y severidad recomendada.

## Tabla de contenidos

1. [Datos financieros](#datos-financieros)
2. [Identificación personal — España/UE](#identificación-españaue)
3. [Identificación personal — Internacional](#identificación-internacional)
4. [Credenciales y secretos](#credenciales)
5. [PII general](#pii-general)
6. [Categorías especiales GDPR Art. 9](#categorías-especiales)

---

## Datos financieros

### IBAN (International Bank Account Number)

- **Formato**: `[A-Z]{2}\d{2}[A-Z0-9]{11,30}` — 2 letras país + 2 dígitos control + BBAN.
- **Longitud por país**: España 24, Francia 27, Alemania 22, Italia 27, Reino Unido 22...
- **Validación**: mover los 4 primeros caracteres al final, convertir letras a números (A=10, B=11, ..., Z=35), calcular `MOD 97 == 1`.
- **Severidad**: 🟠 ALTA.
- **Regulación**: GDPR (dato personal identificativo), PSD2 (Payment Services Directive).
- **Enmascarado típico**: mostrar país + últimos 4 dígitos: `ES**...**1332`.

### PAN (Primary Account Number, número de tarjeta)

- **Formato**: 13-19 dígitos, posiblemente con espacios o guiones cada 4.
- **Validación**: **obligatorio algoritmo de Luhn** — sin él los FP se multiplican.
- **Reglas BIN** (primeros dígitos identifican emisor):
  - Visa: 4xxx, longitud 13/16/19
  - Mastercard: 51-55 o 2221-2720, longitud 16
  - Amex: 34 o 37, longitud 15
  - Discover: 6011, 65, 644-649, longitud 16
  - JCB: 35xx, longitud 16-19
- **Severidad**: 🔴 CRÍTICA (PAN completo en log).
- **Regulación**: PCI-DSS Requisito 3.3 (no mostrar PAN completo), GDPR.
- **Enmascarado PCI-compliant**: máximo BIN (6 primeros) + últimos 4: `453914******6467`. Si no necesitas los 6 primeros, mejor sólo últimos 4: `************6467`.

### CVV / CVC / CVV2

- **Formato**: 3 dígitos (Visa/MC) o 4 (Amex).
- **Validación**: sólo por nombre de variable; por formato es indistinguible.
- **Severidad**: 🔴 CRÍTICA siempre.
- **Regulación**: PCI-DSS Requisito 3.2 — **prohibido almacenar CVV** tras autorización. Loguearlo es violación directa.
- **Enmascarado**: nunca loguear. Punto.

### SWIFT / BIC

- **Formato**: `[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?` — 8 u 11 caracteres.
- **Severidad**: 🟡 MEDIA (menos identificativo que IBAN, pero combinado con cuenta es sensible).
- **Regulación**: GDPR.

### Fecha de caducidad de tarjeta

- **Formato**: MM/YY o MM/YYYY.
- **Severidad**: 🟠 ALTA (combinada con PAN aumenta el riesgo de fraude).
- **Regulación**: PCI-DSS — categoría "cardholder data".

---

## Identificación España/UE

### DNI (Documento Nacional de Identidad, España)

- **Formato**: 8 dígitos + 1 letra. Regex: `\d{8}[A-HJ-NP-TV-Z]`.
- **Validación**: letra = `"TRWAGMYFPDXBNJZSQVHLCKE".charAt(numero % 23)`.
- **Severidad**: 🟠 ALTA.
- **Regulación**: GDPR, LOPDGDD (ley española).
- **Enmascarado típico**: `***5678A` o `12345***A`.

### NIE (Número de Identidad de Extranjero, España)

- **Formato**: letra inicial (X, Y, Z) + 7 dígitos + letra control. Regex: `[XYZ]\d{7}[A-HJ-NP-TV-Z]`.
- **Validación**: X→0, Y→1, Z→2, luego `MOD 23` como DNI.
- **Severidad**: 🟠 ALTA.
- **Regulación**: GDPR, LOPDGDD.

### NIF (personas jurídicas, antes CIF)

- **Formato**: letra organización + 7 dígitos + dígito/letra control. Regex: `[ABCDEFGHJNPQRSUVW]\d{7}[0-9A-J]`.
- **Severidad**: 🟡 MEDIA (dato empresarial, menos sensible).

### Número de Seguridad Social (España)

- **Formato**: 12 dígitos agrupados como `AA 12345678 CC` (provincia + número + control).
- **Severidad**: 🟠 ALTA (da acceso a historial laboral y sanitario).
- **Regulación**: GDPR Art. 9 si se correlaciona con datos sanitarios.

### Pasaporte español

- **Formato**: 3 letras + 6 dígitos. Regex: `[A-Z]{3}\d{6}`.
- **Severidad**: 🟠 ALTA.

---

## Identificación Internacional

### SSN (Social Security Number, US)

- **Formato**: `\d{3}-\d{2}-\d{4}` o 9 dígitos sin separador.
- **Severidad**: 🔴 CRÍTICA (robo de identidad directo en US).
- **Regulación**: Fair Credit Reporting Act, GLBA.

### CURP (México)

- **Formato**: 18 caracteres alfanuméricos con estructura específica.
- **Severidad**: 🟠 ALTA.

### CPF (Brasil)

- **Formato**: `\d{3}\.\d{3}\.\d{3}-\d{2}`.
- **Severidad**: 🟠 ALTA.
- **Regulación**: LGPD (ley brasileña equivalente a GDPR).

### National Insurance Number (UK)

- **Formato**: `[A-Z]{2}\d{6}[A-Z]`.
- **Severidad**: 🟠 ALTA.

---

## Credenciales

### Contraseñas en texto plano

- **Detección**: nombre de variable (`password`, `pwd`, `passwd`, `clave`, `contrasena`).
- **Severidad**: 🔴 CRÍTICA **siempre**, sin excepciones.
- **Regulación**: todas. Violación directa de OWASP ASVS V7.
- **Regla**: nunca, jamás, bajo ninguna circunstancia debe aparecer en un log, ni en DEBUG.

### Tokens de acceso (Bearer, JWT, OAuth)

- **JWT**: `eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+`.
- **Bearer**: contexto `Authorization: Bearer xxxxx`.
- **Severidad**: 🔴 CRÍTICA (equivale a credencial activa).
- **Nota**: aunque estén firmados y tengan expiración, durante su TTL son equivalentes a contraseña.

### API Keys

- **Patrones conocidos**:
  - AWS: `AKIA[0-9A-Z]{16}`
  - Stripe: `sk_live_[0-9a-zA-Z]{24}`, `pk_live_...`
  - GitHub: `ghp_[A-Za-z0-9]{36}`, `gho_`, `ghu_`, `ghs_`, `ghr_`
  - Google: `AIza[0-9A-Za-z\-_]{35}`
  - Slack: `xox[baprs]-[0-9a-zA-Z-]+`
- **Severidad**: 🔴 CRÍTICA.

### Claves privadas

- **Detección**: bloques `-----BEGIN RSA PRIVATE KEY-----`, `-----BEGIN PRIVATE KEY-----`, `-----BEGIN EC PRIVATE KEY-----`.
- **Severidad**: 🔴 CRÍTICA.

### Client Secret / Consumer Secret

- **Detección**: por nombre (`clientSecret`, `consumerSecret`, `oauthSecret`).
- **Severidad**: 🔴 CRÍTICA.

---

## PII general

### Email

- **Formato**: `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}`.
- **Severidad**: 🟡 MEDIA aislado, 🟠 ALTA combinado con otros datos.
- **Regulación**: GDPR — dato personal directamente identificativo.
- **Enmascarado**: `j***@dominio.com`.

### Teléfono

- **Severidad**: 🟡 MEDIA.
- **Regulación**: GDPR.

### Dirección postal

- **Detección**: difícil por formato. Buscar por nombre de variable.
- **Severidad**: 🟡 MEDIA, 🟠 ALTA si es domicilio privado + nombre.
- **Regulación**: GDPR.

### Fecha de nacimiento

- **Severidad**: 🟡 MEDIA. Combinada con ubicación y género da re-identificación ≈87% (estudio Sweeney).
- **Regulación**: GDPR.

### Dirección IP

- **Severidad**: 🔵 BAJA aislada, 🟡 MEDIA combinada.
- **Regulación**: GDPR (considerada PII por el TJUE en Breyer vs. Alemania, 2016).

### Geolocalización precisa (lat/lon)

- **Severidad**: 🟡 MEDIA, 🟠 ALTA si es precisa (>3 decimales) y persistente.
- **Regulación**: GDPR Art. 4.

---

## Categorías especiales

Datos del GDPR Artículo 9 — requieren base legal explícita y **no deben aparecer nunca en logs** salvo necesidad operativa documentada.

- **Datos de salud**: diagnósticos, medicación, pruebas médicas, grupo sanguíneo, discapacidades.
- **Datos genéticos y biométricos**: huellas dactilares, reconocimiento facial, ADN.
- **Origen racial o étnico**.
- **Opiniones políticas**.
- **Convicciones religiosas o filosóficas**.
- **Afiliación sindical**.
- **Vida sexual u orientación sexual**.

**Severidad: 🔴 CRÍTICA siempre**, independientemente del nivel de log.

**Menores de edad**: datos de menores tienen protección reforzada. Si detectas `edad < 18` o `fechaNacimiento` con cálculo que dé menor, marca severidad un nivel por encima del normal.
