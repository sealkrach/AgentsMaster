#!/usr/bin/env python3
"""Valide les skills avant merge (CI). Sans dépendance externe.

Échec (exit 1) si un skill n'a pas de `name`/`description` ou pas de corps.
Avertissement (n'échoue pas) s'il n'a pas d'eval associée (eval/<dir>.jsonl).

La `description` décide du déclenchement de l'agent : c'est l'artefact le plus
important d'un skill, donc on exige qu'elle soit présente et un minimum détaillée.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
EVAL = ROOT / "eval"
MIN_DESC = 30  # caractères mini pour une description utile au déclenchement


def frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    body_start = end
    out, multiline_key = {}, None
    for line in text[3:end].splitlines():
        s = line.strip()
        if multiline_key:  # valeur repliée (description: > sur plusieurs lignes)
            if s and ":" not in s.split(" ")[0]:
                out[multiline_key] = (out.get(multiline_key, "") + " " + s).strip()
                continue
            multiline_key = None
        if ":" in s and not s.startswith("#"):
            k, _, v = s.partition(":")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if v in (">", "|", ">-", "|-"):
                out[k] = ""
                multiline_key = k
            else:
                out[k] = v
    return out


def body_after_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:].strip()
    return text.strip()


def main() -> int:
    if not SKILLS.exists():
        print("Aucun dossier skills/."); return 0
    errors, warnings, checked = [], [], 0
    for sk in sorted(SKILLS.glob("*/SKILL.md")):
        d = sk.parent.name
        if d.startswith("_"):   # _TEMPLATE etc.
            continue
        checked += 1
        text = sk.read_text(encoding="utf-8", errors="ignore")
        fm = frontmatter(text)
        body = body_after_frontmatter(text)
        if not fm.get("name"):
            errors.append(f"{d}: `name` manquant dans le frontmatter")
        desc = fm.get("description", "")
        if not desc:
            errors.append(f"{d}: `description` manquante (elle décide du déclenchement)")
        elif len(desc) < MIN_DESC:
            errors.append(f"{d}: `description` trop courte ({len(desc)}c < {MIN_DESC}) pour un déclenchement fiable")
        if len(body) < 40:
            errors.append(f"{d}: corps du SKILL.md quasi vide")
        if not (EVAL / f"{d}.jsonl").exists():
            warnings.append(f"{d}: pas d'eval associée (eval/{d}.jsonl) — 'train as you build'")

    print(f"Skills vérifiés : {checked}")
    for w in warnings:
        print(f"  ⚠ {w}")
    if errors:
        print("\n❌ ÉCHEC :")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("✅ Tous les skills sont valides.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
