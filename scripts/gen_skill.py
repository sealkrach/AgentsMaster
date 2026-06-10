"""Générateur intelligent de skills pour l'agentathon-lab.

Utilise l'API Anthropic pour produire un SKILL.md complet à partir d'une
description métier en langage naturel.

    python scripts/gen_skill.py --name mon-skill --description "..."
    make gen-skill name=mon-skill description="..."
    python scripts/gen_skill.py --name mon-skill --description "..." --dry-run
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

AVAILABLE_TOOLS = """\
- search_documents(query: str) -> list[dict]      — recherche plein-texte dans le corpus documentaire
- get_document(doc_id: str) -> dict | None        — récupère un document par identifiant
- sql_query(sql: str) -> list[dict]               — SELECT en lecture seule (tables: documents, suppliers, jobs)
- lookup_supplier(name: str) -> dict | None       — recherche un fournisseur par nom
- list_jobs(status: str | None) -> list[dict]     — liste les jobs d'ingestion
- vector_search(query: str, top_k: int) -> list[dict]  — recherche sémantique
- find_entity(name: str) -> list[dict]            — recherche une entité dans le graphe
- graph_neighbors(entity_id: str) -> dict         — voisinage direct d'une entité
- graph_path(src: str, dst: str) -> list[str]     — plus court chemin entre deux entités"""


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _build_system_prompt() -> str:
    invoice_skill = _read(SKILLS_DIR / "invoice-triage" / "SKILL.md")
    entity_skill = _read(SKILLS_DIR / "entity-dossier" / "SKILL.md")
    template = _read(SKILLS_DIR / "_TEMPLATE" / "SKILL.md")

    return f"""\
Tu es un générateur de fichiers SKILL.md pour le projet agentathon-lab.

Un SKILL.md est un fichier markdown avec frontmatter YAML. L'agent IA l'utilise
pour savoir QUAND et COMMENT traiter une tâche métier. Le champ `description` est
LE champ le plus critique : l'agent le lit seul pour décider d'activer ou non le skill.

---

SKILLS DE RÉFÉRENCE — étudie-les et reproduis EXACTEMENT leur style :

Skill 1 (opérationnel) :
```markdown
{invoice_skill}
```

Skill 2 (GraphRAG) :
```markdown
{entity_skill}
```

---

TEMPLATE — respecte cette structure :
```markdown
{template}
```

---

OUTILS DISPONIBLES (à référencer dans allowed-tools et dans les instructions) :
{AVAILABLE_TOOLS}

---

RÈGLES DE GÉNÉRATION :

1. Produis UN SEUL bloc ```markdown ... ``` contenant le SKILL.md complet.
2. Frontmatter YAML obligatoire :
   - `name` : kebab-case exact passé en paramètre
   - `description` : 3-6 phrases, riche en mots-clés métier, se termine par des clauses
     explicites "Use when ..." et "Do NOT use when ..."
   - `license: MIT`
   - `allowed-tools` : liste des outils réellement utilisés dans les instructions
   - `metadata.author: lab.example` et `metadata.version: "0.1"`
3. Corps avec les sections : ## Objectif, ## Quand l'utiliser, ## Instructions,
   ## Format de sortie attendu
4. Instructions : étapes numérotées, déterministes, nommant les outils explicitement
   (en gras ou backticks). Inclure un **Point de validation** avant toute écriture.
5. Langue : français pour la prose, noms d'outils en anglais (tel quel).
6. Longueur cible : 40-80 lignes.
"""


def _call_api(system_prompt: str, name: str, description: str) -> str:
    sys.path.insert(0, str(Path(__file__).parent))
    from _llm import call_llm  # noqa: PLC0415
    user_prompt = (
        f"Génère un SKILL.md pour le skill nommé \"{name}\".\n\n"
        f"Cas métier : {description}"
    )
    try:
        return call_llm(system_prompt, user_prompt, max_tokens=2048)
    except Exception as e:
        print(f"Erreur appel LLM : {e}")
        sys.exit(1)


def _parse_skill_md(text: str) -> str:
    # Cherche un bloc ```markdown ou ```md ou ``` générique
    for pattern in (r"```(?:markdown|md)\n(.*?)```", r"```\n(---.*?)```"):
        blocks = re.findall(pattern, text, re.DOTALL)
        if blocks:
            return blocks[0].strip()
    # Fallback : utiliser tout le texte si ça commence par ---
    stripped = text.strip()
    if stripped.startswith("---"):
        return stripped
    return ""


def _validate(content: str, name: str) -> list[str]:
    issues = []
    if not content.startswith("---"):
        issues.append("Le contenu ne commence pas par '---' (frontmatter manquant).")
    if f"name: {name}" not in content:
        issues.append(f"Le champ 'name: {name}' est absent du frontmatter.")
    if "## Instructions" not in content:
        issues.append("La section '## Instructions' est absente.")
    if "## Objectif" not in content:
        issues.append("La section '## Objectif' est absente.")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Génère un SKILL.md complet avec l'IA Anthropic."
    )
    parser.add_argument("--name", required=True, help="Nom du skill (kebab-case)")
    parser.add_argument("--description", required=True, help="Description du cas métier")
    parser.add_argument("--dry-run", action="store_true", help="Affiche sans écrire")
    args = parser.parse_args()

    print("[STEP:validate]")
    # Validation du nom
    if not re.fullmatch(r"[a-z0-9-]+", args.name):
        print(f"Erreur : nom invalide '{args.name}'. Utilisez uniquement minuscules, chiffres et tirets.")
        return 1

    skill_dir = SKILLS_DIR / args.name
    if skill_dir.exists():
        print(f"Erreur : le skill '{args.name}' existe déjà dans {skill_dir}.")
        return 1

    print(f"Génération du skill '{args.name}'…")
    print("[STEP:build_prompt]")
    system_prompt = _build_system_prompt()
    print("[STEP:api_call]")
    raw = _call_api(system_prompt, args.name, args.description)
    print("[STEP:parse]")
    content = _parse_skill_md(raw)
    if not content:
        print("Erreur : la réponse du modèle ne contient pas de SKILL.md valide.")
        print("Réponse brute :")
        print(raw[:500])
        return 1

    issues = _validate(content, args.name)

    if args.dry_run:
        print("=== SKILL.md (dry-run) ===")
        print(content)
        if issues:
            print("\n⚠ Avertissements :")
            for i in issues:
                print(f"  - {i}")
        return 0

    if issues:
        print("⚠ Avertissements de validation (le fichier sera quand même créé) :")
        for i in issues:
            print(f"  - {i}")

    print("[STEP:write]")
    skill_dir.mkdir(parents=True)
    (skill_dir / "references").mkdir()
    (skill_dir / "SKILL.md").write_text(content + "\n", encoding="utf-8")

    print(f"✓ Skill créé : skills/{args.name}/SKILL.md")
    print(f"  → Testez avec : make up-inproc  puis tapez dans l'UI : {args.description[:60]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
