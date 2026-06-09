"""Index léger des skills : lit le frontmatter de chaque SKILL.md, sans dépendance YAML.
Sert à exposer dans /info la liste des skills (nom + description) — la `description`
étant ce qui décide du déclenchement, c'est l'info la plus utile à montrer."""
from __future__ import annotations

from pathlib import Path


def _frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    out: dict = {}
    for line in text[3:end].splitlines():
        s = line.strip()
        if ":" in s and not s.startswith("#"):
            k, _, v = s.partition(":")
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def list_skills(skills_dir: str) -> list[dict]:
    root = Path(skills_dir)
    if not root.exists():
        return []
    out = []
    for sk in sorted(root.glob("*/SKILL.md")):
        fm = _frontmatter(sk.read_text(encoding="utf-8", errors="ignore"))
        out.append({
            "name": fm.get("name") or sk.parent.name,
            "description": (fm.get("description") or "")[:200],
            "dir": sk.parent.name,
        })
    return out
