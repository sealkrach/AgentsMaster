"""Analyse statique de sécurité pour le code MCP généré.

Règles READ-ONLY :
  - Pas de SQL destructeur (INSERT/UPDATE/DELETE/DROP/ALTER/TRUNCATE/CREATE)
  - Pas de méthodes HTTP non-GET/HEAD
  - Pas de subprocess, os.system, os.popen, eval, exec
  - Pas d'écriture de fichiers hors /tmp
"""
from __future__ import annotations

import re

_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE)\b",
    re.IGNORECASE,
)
_HTTP_WRITE = re.compile(
    r"\.(post|put|patch|delete)\s*\(",
    re.IGNORECASE,
)
_DANGEROUS = re.compile(
    r"\b(subprocess|os\.system|os\.popen|eval|exec)\s*[(\.]"
)
_FILE_WRITE = re.compile(
    r'open\s*\([^)]*["\'](?:w|a|x|wb|ab)["\']'
)


def analyze(code: str) -> tuple[bool, list[str]]:
    """Return (is_safe, violations). is_safe is True when no violations found."""
    violations: list[str] = []

    matches = _SQL.findall(code)
    if matches:
        violations.append(f"SQL destructeur : {sorted({m.upper() for m in matches})}")

    if _HTTP_WRITE.search(code):
        violations.append("Méthode HTTP non-GET/HEAD détectée (POST/PUT/PATCH/DELETE)")

    dangerous = _DANGEROUS.findall(code)
    if dangerous:
        violations.append(f"Appels dangereux : {dangerous}")

    if _FILE_WRITE.search(code):
        violations.append("Écriture de fichier détectée (mode w/a/x — utilisez /tmp)")

    return len(violations) == 0, violations
