#!/usr/bin/env python3
"""
scan_logs.py — Primer barrido para encontrar logs potencialmente inseguros en Java.

Uso:
    python3 scan_logs.py <ruta_proyecto> [--output hallazgos.json] [--min-severity low]

Este script es una AYUDA. Produce candidatos con regex; no entiende semántica.
Revisa los resultados con criterio — habrá falsos positivos y falsos negativos.

El usuario final de la skill debe revisar cada hallazgo manualmente.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Iterator


# ──────────────────────────────────────────────────────────────────────
# Patrones de sinks (puntos de salida)
# ──────────────────────────────────────────────────────────────────────

SINK_PATTERNS: dict[str, re.Pattern] = {
    "slf4j_logger": re.compile(
        r"\b(log|logger|LOG|LOGGER)\s*\.\s*(trace|debug|info|warn|error)\s*\("
    ),
    "log4j_fatal": re.compile(
        r"\b(log|logger|LOG|LOGGER)\s*\.\s*fatal\s*\("
    ),
    "jul_logger": re.compile(
        r"\b(log|logger)\s*\.\s*(finest|finer|fine|config|warning|severe)\s*\("
    ),
    "system_out": re.compile(
        r"\bSystem\s*\.\s*(out|err)\s*\.\s*(print|println|printf|format)\s*\("
    ),
    "print_stack_trace": re.compile(
        r"\.printStackTrace\s*\("
    ),
    "exception_concat": re.compile(
        r"throw\s+new\s+\w+(?:Exception|Error)\s*\(\s*\"[^\"]*\"\s*\+"
    ),
    "mdc_put": re.compile(
        r"\b(MDC|ThreadContext)\s*\.\s*put\s*\("
    ),
    "lombok_data": re.compile(
        r"@Data\b|@ToString(?!\s*\(\s*(exclude|of|onlyExplicitlyIncluded))"
    ),
}

# ──────────────────────────────────────────────────────────────────────
# Patrones de sources (datos sensibles)
# Por nombre de variable y por formato de contenido
# ──────────────────────────────────────────────────────────────────────

# Nombres de variables/campos/parámetros que sugieren dato sensible
# Se busca como palabra entera (word boundary), case-insensitive.
SENSITIVE_NAMES: dict[str, tuple[str, ...]] = {
    "financial_critical": (
        "cvv", "cvc", "cvv2", "securitycode", "codigoseguridad",
    ),
    "financial_high": (
        "iban", "bic", "swift", "accountnumber", "numerocuenta", "codigoiban",
        "cardnumber", "creditcard", "debitcard", "pan", "tarjeta", "numtarjeta",
        "expirationdate", "expirydate", "fechacaducidad", "validthru",
    ),
    "identity_high": (
        "dni", "nie", "nif", "documento", "docidentidad", "identitynumber",
        "ssn", "socialsecurity", "numseguridadsocial", "nss", "nuss",
        "passport", "pasaporte", "passportnumber",
        "curp", "cpf", "cnpj", "rfc",
        "driverlicense", "carnetconducir", "permisoconducir",
    ),
    "identity_medium": (
        "taxid", "vatnumber",
    ),
    "credential_critical": (
        "password", "passwd", "pwd", "clave", "contrasena", "contrasenya",
        "secret", "apikey", "api_key", "apitoken", "accesstoken", "refreshtoken",
        "privatekey", "clavesecreta", "clavejwt",
        "token", "bearertoken", "jwt", "authtoken",
        "clientsecret", "consumersecret",
    ),
    "pii_medium": (
        "email", "correo", "correoelectronico", "mail",
        "phone", "phonenumber", "telefono", "movil", "celular", "mobile",
        "birthdate", "fechanacimiento", "dob", "dateofbirth",
        "address", "direccion",
    ),
    "pii_low": (
        "ip", "ipaddress", "clientip",
        "zipcode", "postalcode", "codigopostal",
    ),
    "special_critical": (
        "healthdata", "datossanitarios", "diagnosis", "diagnostico",
        "bloodtype", "gruposanguineo",
        "biometric", "fingerprint", "huelladactilar",
        "religion", "politicalview", "orientation", "ethnicity",
    ),
}

# Patrones de contenido literal (strings hardcodeados con formato sospechoso)
CONTENT_PATTERNS: dict[str, tuple[str, re.Pattern]] = {
    "iban_literal": (
        "high",
        re.compile(r"\"[A-Z]{2}\d{2}[A-Z0-9]{11,30}\""),
    ),
    "dni_literal": (
        "high",
        re.compile(r"\"\d{8}[A-HJ-NP-TV-Z]\""),
    ),
    "nie_literal": (
        "high",
        re.compile(r"\"[XYZ]\d{7}[A-HJ-NP-TV-Z]\""),
    ),
    "jwt_literal": (
        "critical",
        re.compile(r"\"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\""),
    ),
    "aws_key": (
        "critical",
        re.compile(r"\"AKIA[0-9A-Z]{16}\""),
    ),
    "stripe_key": (
        "critical",
        re.compile(r"\"(sk|pk|rk)_(live|test)_[0-9a-zA-Z]{24,}\""),
    ),
    "github_token": (
        "critical",
        re.compile(r"\"gh[pousr]_[A-Za-z0-9]{36}\""),
    ),
    "private_key_block": (
        "critical",
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ),
    "ssn_literal": (
        "critical",
        re.compile(r"\"\d{3}-\d{2}-\d{4}\""),
    ),
}

# Regex para "nombre sospechoso": detecta tanto identificadores como accesos a getters
# Ejemplos que casa: iban, customer.iban, getIban(), .iban
# Se construye al vuelo desde SENSITIVE_NAMES.

def _build_name_regex(names: tuple[str, ...]) -> re.Pattern:
    # Ordenar por longitud desc para preferir coincidencias largas (pan antes que p)
    escaped = sorted((re.escape(n) for n in names), key=len, reverse=True)
    alt = "|".join(escaped)
    # Word boundary-ish; permitimos mayúsculas intercaladas porque "cardNumber" matcheará "cardnumber" ci
    return re.compile(rf"(?i)(?<![A-Za-z0-9_])({alt})(?![A-Za-z0-9_])")


SENSITIVE_NAME_REGEX: dict[str, re.Pattern] = {
    category: _build_name_regex(names)
    for category, names in SENSITIVE_NAMES.items()
}

# Pistas de enmascarado — si aparecen cerca, probablemente es FP
MASKING_HINTS = re.compile(
    r"\b(mask|obfuscate|redact|sanitize|anonymize|hash|encrypt)\w*\s*\(",
    re.IGNORECASE,
)

# Severidades por categoría
CATEGORY_SEVERITY: dict[str, str] = {
    "financial_critical": "critical",
    "financial_high": "high",
    "identity_high": "high",
    "identity_medium": "medium",
    "credential_critical": "critical",
    "pii_medium": "medium",
    "pii_low": "low",
    "special_critical": "critical",
}

SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


# ──────────────────────────────────────────────────────────────────────
# Lógica de escaneo
# ──────────────────────────────────────────────────────────────────────

@dataclass
class Finding:
    file: str
    line: int
    column: int
    sink: str
    severity: str
    categories: list[str]
    matched_names: list[str]
    matched_literals: list[str]
    snippet: str
    likely_false_positive: bool = False
    fp_reason: str = ""


def find_java_files(root: Path) -> Iterator[Path]:
    """Itera todos los .java dentro de root, ignorando typical build dirs."""
    ignore_dirs = {"target", "build", "out", ".gradle", ".idea", "node_modules", ".git"}
    for path in root.rglob("*.java"):
        if any(part in ignore_dirs for part in path.parts):
            continue
        yield path


def analyze_line(line: str, lineno: int, file_path: str, surrounding: list[str]) -> list[Finding]:
    """Analiza una línea y devuelve los findings que genera."""
    findings: list[Finding] = []

    # 1. Detectar sink en la línea
    sink_hits: list[tuple[str, int]] = []
    for sink_name, pattern in SINK_PATTERNS.items():
        for m in pattern.finditer(line):
            sink_hits.append((sink_name, m.start()))

    if not sink_hits:
        return []

    # 2. Para cada sink, buscar sources en la misma línea
    for sink_name, sink_col in sink_hits:
        matched_names: list[tuple[str, str]] = []  # (category, name)
        matched_literals: list[tuple[str, str, str]] = []  # (category, severity, text)

        # Sources por nombre
        for category, regex in SENSITIVE_NAME_REGEX.items():
            for m in regex.finditer(line):
                matched_names.append((category, m.group(1)))

        # Sources por contenido literal
        for kind, (severity, regex) in CONTENT_PATTERNS.items():
            for m in regex.finditer(line):
                matched_literals.append((kind, severity, m.group(0)[:40]))

        # El sink lombok_data no requiere source en la misma línea para disparar —
        # es suficiente con la anotación si la clase tiene campos sensibles.
        # Pero para simplificar aquí, sólo reportamos si hay pistas en las próximas 30 líneas.
        if sink_name == "lombok_data":
            surrounding_text = "\n".join(surrounding)
            for category, regex in SENSITIVE_NAME_REGEX.items():
                for m in regex.finditer(surrounding_text):
                    matched_names.append((category, m.group(1)))

        if not matched_names and not matched_literals:
            continue

        # Calcular severidad máxima
        severities = [CATEGORY_SEVERITY[c] for c, _ in matched_names]
        severities.extend([s for _, s, _ in matched_literals])
        max_sev = max(severities, key=lambda s: SEVERITY_RANK[s])

        # Detectar si es posible FP por enmascarado presente EN LA MISMA LÍNEA.
        # Buscar en contexto amplio daría demasiados FP (ver test L35).
        is_fp = False
        fp_reason = ""
        if MASKING_HINTS.search(line):
            is_fp = True
            fp_reason = "Llamada a función de enmascarado/hash en la misma línea"

        # Tests: nota informativa
        if "/test/" in file_path.replace("\\", "/").lower() or file_path.lower().endswith(
            ("test.java", "tests.java", "it.java")
        ):
            if not is_fp:
                is_fp = True
                fp_reason = "Archivo de test — posible dato sintético"

        findings.append(
            Finding(
                file=file_path,
                line=lineno,
                column=sink_col,
                sink=sink_name,
                severity=max_sev,
                categories=sorted({c for c, _ in matched_names}),
                matched_names=sorted({n for _, n in matched_names}),
                matched_literals=[f"{k}: {t}" for k, _, t in matched_literals],
                snippet=line.rstrip(),
                likely_false_positive=is_fp,
                fp_reason=fp_reason,
            )
        )

    return findings


def scan_file(path: Path) -> list[Finding]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        print(f"  [!] no se pudo leer {path}: {e}", file=sys.stderr)
        return []

    lines = text.splitlines()
    findings: list[Finding] = []

    for i, line in enumerate(lines, start=1):
        # Ignora comentarios enteros (pero no inline, porque algo como
        # "log.info(...)" en mitad de comentario es raro pero posible)
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("*"):
            continue

        # Contexto: 5 líneas antes y 15 después (para lombok y clases)
        start_ctx = max(0, i - 6)
        end_ctx = min(len(lines), i + 15)
        surrounding = lines[start_ctx:end_ctx]

        findings.extend(analyze_line(line, i, str(path), surrounding))

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Escanea código Java en busca de logs con datos sensibles."
    )
    parser.add_argument("root", type=Path, help="Ruta al proyecto o archivo Java")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Ruta del JSON de salida (si se omite, imprime por stdout)",
    )
    parser.add_argument(
        "--min-severity",
        choices=["low", "medium", "high", "critical"],
        default="low",
        help="Severidad mínima a reportar",
    )
    parser.add_argument(
        "--exclude-tests",
        action="store_true",
        help="No analizar archivos de test",
    )
    args = parser.parse_args()

    if not args.root.exists():
        print(f"Ruta no encontrada: {args.root}", file=sys.stderr)
        return 1

    min_rank = SEVERITY_RANK[args.min_severity]

    # Recolectar archivos
    if args.root.is_file() and args.root.suffix == ".java":
        files = [args.root]
    else:
        files = list(find_java_files(args.root))

    if args.exclude_tests:
        files = [
            f for f in files
            if "/test/" not in str(f).replace("\\", "/").lower()
            and not str(f).lower().endswith(("test.java", "tests.java", "it.java"))
        ]

    print(f"Escaneando {len(files)} archivos Java...", file=sys.stderr)

    all_findings: list[Finding] = []
    for f in files:
        all_findings.extend(scan_file(f))

    # Filtrar por severidad mínima
    filtered = [f for f in all_findings if SEVERITY_RANK[f.severity] >= min_rank]

    # Agrupar estadísticas
    stats = {"critical": 0, "high": 0, "medium": 0, "low": 0, "total": len(filtered)}
    stats_fp = {"critical": 0, "high": 0, "medium": 0, "low": 0, "total": 0}
    for f in filtered:
        stats[f.severity] += 1
        if f.likely_false_positive:
            stats_fp[f.severity] += 1
            stats_fp["total"] += 1

    output = {
        "scanned_files": len(files),
        "total_findings": len(filtered),
        "findings_by_severity": stats,
        "likely_false_positives_by_severity": stats_fp,
        "findings": [asdict(f) for f in filtered],
    }

    payload = json.dumps(output, indent=2, ensure_ascii=False)

    if args.output:
        args.output.write_text(payload, encoding="utf-8")
        print(f"Hallazgos escritos en {args.output}", file=sys.stderr)
        print(
            f"  Total: {stats['total']}  "
            f"(🔴 {stats['critical']}  🟠 {stats['high']}  "
            f"🟡 {stats['medium']}  🔵 {stats['low']})",
            file=sys.stderr,
        )
        print(
            f"  Posibles FP: {stats_fp['total']}",
            file=sys.stderr,
        )
    else:
        print(payload)

    return 0


if __name__ == "__main__":
    sys.exit(main())
