"""Garde applicative : n'autorise qu'UNE requête SELECT/WITH en lecture seule.

⚠ Ce n'est PAS la vraie garantie — la vraie garantie est un rôle Postgres en
lecture seule (GRANT SELECT). Ceci est une défense en profondeur, sans dépendance.
"""
from __future__ import annotations

import re

_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|COPY|CALL|"
    r"MERGE|REPLACE|VACUUM|REINDEX|REFRESH|LISTEN|NOTIFY|DO|EXECUTE|SET|RESET|"
    r"LOCK|COMMENT|INTO)\b",
    re.IGNORECASE,
)
_COMMENT = re.compile(r"(--[^\n]*|/\*.*?\*/)", re.DOTALL)


class SqlNotAllowed(ValueError):
    pass


def ensure_readonly_select(sql: str) -> str:
    """Renvoie la requête nettoyée si elle est un SELECT/WITH unique en lecture seule.
    Lève SqlNotAllowed sinon."""
    if not sql or not sql.strip():
        raise SqlNotAllowed("requête vide")
    cleaned = _COMMENT.sub(" ", sql).strip().rstrip(";").strip()
    if ";" in cleaned:
        raise SqlNotAllowed("plusieurs instructions interdites")
    first = cleaned.lstrip("(").lstrip()
    head = first.split(None, 1)[0].upper() if first else ""
    if head not in ("SELECT", "WITH"):
        raise SqlNotAllowed("seuls SELECT/WITH sont autorisés")
    if _FORBIDDEN.search(cleaned):
        raise SqlNotAllowed("mot-clé non autorisé détecté")
    return cleaned
