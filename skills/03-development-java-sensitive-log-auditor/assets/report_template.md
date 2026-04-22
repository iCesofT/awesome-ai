# Plantilla de informe

Usa esta estructura para todos los informes de auditoría. Personaliza las secciones según los hallazgos reales.

---

# Auditoría de trazas sensibles — `<nombre del proyecto / módulo>`

**Fecha**: `<YYYY-MM-DD>`
**Alcance**: `<archivos / paquetes / branches revisados>`
**Analista**: Claude (java-sensitive-log-auditor skill)

## 1. Resumen ejecutivo

| Severidad | Hallazgos | Archivos afectados |
|---|---|---|
| 🔴 Crítica | N | N |
| 🟠 Alta | N | N |
| 🟡 Media | N | N |
| 🔵 Baja | N | N |
| **Total** | **N** | **N** |

**Principales riesgos identificados:**

- `<resumen en 3-5 bullets de los problemas sistémicos>`

**Cumplimiento potencialmente afectado:**

- `<GDPR / PCI-DSS / HIPAA / LOPDGDD según aplique>`

**Veredicto**: `<APTO / APTO CON ACCIONES / NO APTO para producción>`

---

## 2. Hallazgos detallados

### 🔴 H-001 — `<título corto descriptivo>`

- **Archivo**: `src/main/java/com/example/.../Xxx.java`
- **Línea(s)**: 42-45
- **Sink**: `log.info(...)` con concatenación
- **Dato sensible**: PAN (número de tarjeta completo)
- **Confianza**: Alta
- **Cumplimiento**: PCI-DSS 3.3, GDPR Art. 32

**Fragmento (con dato enmascarado para el informe):**

```java
public void procesarPago(Pago pago) {
    log.info("Procesando tarjeta " + pago.getCardNumber());  // ← fuga
    //                                ^^^^^^^^^^^^^^^^^^^
    // pago.getCardNumber() devuelve PAN completo (16 dígitos)
}
```

**Por qué es un problema:**

`<explicación breve — por qué este dato no puede ir al log en este nivel>`

**Corrección propuesta:**

```diff
 public void procesarPago(Pago pago) {
-    log.info("Procesando tarjeta " + pago.getCardNumber());
+    log.info("Procesando tarjeta {}", SensitiveDataMask.maskPan(pago.getCardNumber()));
 }
```

---

### 🟠 H-002 — `<título>`

`<mismo formato>`

---

### 🟡 H-003 — `<título>`

`<mismo formato>`

---

## 3. Patrones sistémicos (refactors globales sugeridos)

Problemas que aparecen en múltiples archivos y que merecen una acción transversal:

### S-001 — `@Data` de Lombok sin exclusiones en entidades de dominio

- **Afecta a**: `Customer.java`, `Account.java`, `Payment.java`, `User.java` (4 archivos)
- **Propuesta**: añadir `@ToString(exclude = {...})` o migrar a `@ToString.Exclude` por campo.
- **Prioridad**: Alta — cualquier `log.info("... {}", entity)` propaga el problema.

### S-002 — Mensajes de excepción con datos de entrada

- **Afecta a**: `ValidationService.java` (12 ocurrencias), `PaymentService.java` (7)
- **Propuesta**: crear `ValidationException` con un `field` y un `reason` en lugar del valor crudo.

### S-003 — `application-prod.properties` con niveles DEBUG

- **Afecta a**: `application-prod.properties` línea 34
- **Propuesta**: `logging.level.org.hibernate.SQL=WARN`, retirar `spring.jpa.show-sql=true`.

---

## 4. Falsos positivos descartados

Menciona los candidatos que analizaste pero descartaste, para que el revisor pueda verificar tu criterio:

| Archivo | Línea | Por qué se descartó |
|---|---|---|
| `IbanValidator.java` | 15 | Constante con regex, no un valor real |
| `PaymentServiceTest.java` | 88 | Test unitario con PAN de prueba Visa (`4111111111111111`) |

---

## 5. Recomendaciones generales

1. **Crear `SensitiveDataMask` utility class** si no existe (ver `remediation_patterns.md`).
2. **Añadir tests que validen** que ciertos logs no contienen patrones sensibles (ej: `assertThat(logCapturer.getLogs()).doesNotContain(iban)`).
3. **Configurar filtro de Logback/Log4j2** como red de seguridad (no como solución primaria).
4. **Code review obligatorio** para PRs que toquen `*Service.java`, `*Controller.java` y entidades.
5. **Considerar herramientas estáticas**: SpotBugs con plugin `find-sec-bugs`, PMD con regla custom, SonarQube regla `S6437`.

---

## 6. Checklist para el equipo

- [ ] Revisar los H-001 a H-N críticos antes del próximo deploy.
- [ ] Aplicar los refactors sistémicos S-001 a S-N en las próximas 2 semanas.
- [ ] Añadir al `CONTRIBUTING.md` la regla: "No loguear entidades de dominio completas".
- [ ] Formación breve al equipo sobre logging seguro (1h).

---

## Anexo A — Metodología

Esta auditoría se realizó analizando:

- Loggers: SLF4J, Log4j, Log4j2, JUL.
- Salidas directas: `System.out`, `System.err`, `printStackTrace()`.
- `toString()` de entidades y DTOs (Lombok `@Data`, `@ToString`, records).
- Mensajes de excepción con concatenación de variables.
- `MDC` / `ThreadContext`.
- Configuración de logging (`application*.properties`, `logback*.xml`, `log4j2.xml`).

**Limitaciones**: este análisis es estático y textual. No ejecuta el código ni sigue el flujo de datos en runtime. Un dato que entra en una variable con nombre neutro ("data", "value") puede contener información sensible y pasar inadvertido. Los hallazgos son candidatos de alta probabilidad — cada uno requiere validación por alguien con conocimiento del dominio.
