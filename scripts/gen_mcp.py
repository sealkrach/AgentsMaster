"""Générateur intelligent de serveurs MCP pour l'agentathon-lab.

Utilise l'API Anthropic pour produire, à partir d'une description en langage naturel :
  - Une classe mock source (mock_sources/_generated.py)
  - Un serveur FastMCP (mcp_servers/servers_generated.py)
  - Des outils inproc LangChain (runtime/tools_generated.py)
  - Une entrée de config (runtime/config_generated.py)

    python scripts/gen_mcp.py --name mon-serveur --description "..."
    make gen-mcp name=mon-serveur description="..."
    python scripts/gen_mcp.py --name mon-serveur --description "..." --dry-run
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

_SERVERS_PY  = REPO_ROOT / "mcp_servers" / "servers.py"
_SERVERS_GEN = REPO_ROOT / "mcp_servers" / "servers_generated.py"
_MOCK_GEN    = REPO_ROOT / "mock_sources" / "_generated.py"
_TOOLS_GEN   = REPO_ROOT / "runtime" / "tools_generated.py"
_CONFIG_GEN  = REPO_ROOT / "runtime" / "config_generated.py"

_MOCK_HEADER = (
    '"""Sources mock générées. Ne pas éditer manuellement'
    ' — utilisez scripts/gen_mcp.py."""\n'
    "from __future__ import annotations\n"
    "from typing import Any\n"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _to_camel(name: str) -> str:
    """'audit-trail' → 'AuditTrail'"""
    return "".join(p.capitalize() for p in re.split(r"[-_]", name))


def _to_py(name: str) -> str:
    """'audit-trail' → 'audit_trail'  (nom de fonction Python valide)"""
    return name.replace("-", "_")


def _find_existing_ports() -> set[int]:
    text = _read(_SERVERS_PY) + _read(_SERVERS_GEN)
    return {int(p) for p in re.findall(r"\b9\d{3}\b", text)}


def _find_existing_names() -> set[str]:
    text = _read(_SERVERS_PY) + _read(_SERVERS_GEN)
    return set(re.findall(r'"([a-z0-9-]+)"\s*:\s*9\d{3}', text))


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

def _build_system_prompt() -> str:
    servers_ref = _read(_SERVERS_PY)
    store_ref   = _read(REPO_ROOT / "mock_sources" / "store.py")
    relational_ref = _read(REPO_ROOT / "mock_sources" / "relational.py")

    return f"""\
Tu es un générateur de code Python pour le projet agentathon-lab.
Tu génères un nouveau serveur MCP (FastMCP) et son mock backend.

---
IMPLÉMENTATION DE RÉFÉRENCE — reproduis EXACTEMENT ce style :

```python
{servers_ref}
```

EXEMPLES DE MOCK SOURCE :
```python
{store_ref}
```
```python
{relational_ref}
```

---
RÈGLES :

Produis EXACTEMENT 3 blocs Python avec ces marqueurs sur la ligne d'ouverture :

1. ```python [MOCK_SOURCE]
   Classe `<CamelCase>Source` :
   - `__init__(self, data: dict[str, Any]) -> None` : charge les données
   - 2 à 3 méthodes publiques (même API que les outils MCP)
   - Stdlib Python uniquement (pas de dépendances externes)
   ```

2. ```python [MCP_SERVER]
   Fonction `_<py_name>() -> FastMCP:` où <py_name> utilise des underscores (pas de tirets) :
   - `mcp = FastMCP("<name>", host=HOST, port=PLACEHOLDER_PORT)`
   - Instance module-level de la source : `_<PY_NAME>_SOURCE = <CamelCase>Source({{}})`
   - 2 à 3 outils `@mcp.tool()` avec docstrings en français
   - Import en tête : `from mock_sources._generated import <CamelCase>Source`
   - Termine par : `return mcp`
   ```

3. ```python [INPROC_TOOLS]
   Mêmes outils au format LangChain :
   - `from langchain_core.tools import tool`
   - Instance module-level : `_<PY_NAME>_SRC = <CamelCase>Source({{}})`
   - Fonctions `@tool` avec mêmes noms/signatures/docstrings que le serveur MCP
   - Termine par : `GENERATED_INPROC_TOOLS_<NAME_UPPER> = [fn1, fn2, ...]`
   ```

Contraintes :
- `from __future__ import annotations` en première ligne de chaque bloc
- Port : le mot-clé exact `PLACEHOLDER_PORT` (sans guillemets)
- Pas de bloc `if __name__ == "__main__"`
- Noms de fonctions Python avec underscores (pas de tirets)
"""


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

def _call_api(system_prompt: str, name: str, description: str, camel: str, py_name: str) -> str:
    sys.path.insert(0, str(Path(__file__).parent))
    from _llm import call_llm  # noqa: PLC0415
    user_prompt = (
        f'Génère un serveur MCP nommé "{name}" (port PLACEHOLDER_PORT).\n\n'
        f"Description de la source de données : {description}\n\n"
        f"Nom CamelCase de la classe mock : {camel}Source\n"
        f"Nom Python de la fonction factory : _{py_name}  (underscores, pas de tirets)"
    )
    try:
        return call_llm(system_prompt, user_prompt, max_tokens=4096)
    except Exception as e:
        print(f"Erreur appel LLM : {e}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _parse_blocks(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for marker in ("MOCK_SOURCE", "MCP_SERVER", "INPROC_TOOLS"):
        m = re.search(rf"```python\s+\[{marker}\]\s*\n(.*?)```", text, re.DOTALL)
        if m:
            result[marker] = m.group(1).strip()

    # Fallback par ordre si marqueurs absents
    if len(result) < 3:
        all_blocks = re.findall(r"```python\n(.*?)```", text, re.DOTALL)
        for i, key in enumerate(("MOCK_SOURCE", "MCP_SERVER", "INPROC_TOOLS")):
            if key not in result and i < len(all_blocks):
                result[key] = all_blocks[i].strip()

    return result


def _extract_tool_names(block: str) -> list[str]:
    """Noms des fonctions @tool dans un bloc de code."""
    return re.findall(r"^def\s+([a-z_][a-z0-9_]*)\s*\(", block, re.MULTILINE)


# ---------------------------------------------------------------------------
# File writers
# ---------------------------------------------------------------------------

def _write_mock_gen(camel: str, block: str) -> None:
    existing = _read(_MOCK_GEN)
    if f"class {camel}Source" in existing:
        print(f"  ⚠  Classe {camel}Source déjà présente, ignorée.")
        return
    if existing:
        content = existing.rstrip() + "\n\n\n" + block + "\n"
    else:
        content = _MOCK_HEADER + "\n\n" + block + "\n"
    _write(_MOCK_GEN, content)


def _servers_gen_parts(content: str) -> tuple[str, list[tuple[str, int]]]:
    """Sépare (bloc fonctions, liste (name, port) existants) dans servers_generated.py."""
    known: list[tuple[str, int]] = [
        (m[0], int(m[1]))
        for m in re.findall(r'"([a-z0-9-]+)"\s*:\s*(9\d{3})', content)
        if "GENERATED_PORTS" not in content[: content.find(m[0])]  # dans le dict
        or True  # simplifié : on prend tous
    ]
    # Extraire uniquement les ports du dict GENERATED_PORTS
    ports_match = re.search(r"GENERATED_PORTS\s*[:\w\[\],\s]*=\s*\{(.*?)\}", content, re.DOTALL)
    if ports_match:
        known = [
            (m[0], int(m[1]))
            for m in re.findall(r'"([a-z0-9-]+)"\s*:\s*(9\d{3})', ports_match.group(1))
        ]
    # Tout ce qui précède GENERATED_PORTS (fonctions factory)
    split_marker = "GENERATED_PORTS"
    funcs = content.split(split_marker)[0].rstrip() if split_marker in content else content.rstrip()
    return funcs, known


def _write_servers_gen(name: str, port: int, camel: str, py_name: str, server_block: str) -> None:
    existing = _read(_SERVERS_GEN)
    funcs_part, known = _servers_gen_parts(existing)

    # Supprimer le header de docstring si présent (éviter doublons)
    header_doc = '"""Serveurs MCP générés. Ne pas éditer manuellement — utilisez scripts/gen_mcp.py."""'
    if funcs_part.startswith(header_doc):
        funcs_part = funcs_part[len(header_doc):].lstrip("\n")

    # Ajouter l'import de la source si absent
    import_line = f"from mock_sources._generated import {camel}Source"
    if import_line not in funcs_part:
        future_line = "from __future__ import annotations"
        if future_line in funcs_part:
            funcs_part = funcs_part.replace(
                future_line, future_line + "\n" + import_line, 1
            )
        else:
            funcs_part = import_line + "\n\n" + funcs_part

    # Ajouter la nouvelle fonction factory
    funcs_part = funcs_part + "\n\n\n" + server_block

    # Reconstruire les dicts (all_servers = connus + nouveau)
    all_servers = known + [(name, port)]
    ports_lines    = "\n".join(f'    "{n}": {p},' for n, p in all_servers)
    factories_lines = "\n".join(f'    "{n}": _{_to_py(n)},' for n, _ in all_servers)

    new_content = (
        header_doc + "\n"
        + funcs_part.strip() + "\n\n\n"
        + f"GENERATED_PORTS: dict[str, int] = {{\n{ports_lines}\n}}\n"
        + f"GENERATED_FACTORIES: dict = {{\n{factories_lines}\n}}\n"
    )
    _write(_SERVERS_GEN, new_content)


def _tools_gen_parts(content: str) -> tuple[str, list[str]]:
    """Sépare (bloc fonctions, noms d'outils existants) dans tools_generated.py."""
    marker = "GENERATED_INPROC_TOOLS"
    if marker not in content:
        return content.rstrip(), []
    parts = content.rsplit(marker, 1)
    funcs_part = parts[0].rstrip()
    # Extraire les noms de la liste
    list_content = parts[1]
    existing_names = re.findall(r"\b([a-z][a-z0-9_]+)\b", list_content)
    # Filtrer les mots-clés Python courants
    _KW = {"list", "dict", "str", "int", "float", "bool", "None", "True", "False",
           "type", "from", "import", "as", "def", "return", "if", "else", "for"}
    return funcs_part, [n for n in existing_names if n not in _KW and len(n) > 2]


def _write_tools_gen(inproc_block: str, tool_names: list[str]) -> None:
    existing = _read(_TOOLS_GEN)
    funcs_part, existing_names = _tools_gen_parts(existing)

    # Supprimer le header de docstring si présent
    header_doc = '"""Outils inproc générés. Ne pas éditer manuellement — utilisez scripts/gen_mcp.py."""'
    if funcs_part.startswith(header_doc):
        funcs_part = funcs_part[len(header_doc):].lstrip("\n")

    # Nettoyer le bloc inproc : retirer la liste GENERATED_INPROC_TOOLS_<NAME>
    clean_block = re.sub(
        r"\nGENERATED_INPROC_TOOLS_\w+\s*=\s*\[.*?\]", "", inproc_block, flags=re.DOTALL
    ).rstrip()

    funcs_part = funcs_part + "\n\n\n" + clean_block

    all_names = existing_names + tool_names
    list_lines = "\n".join(f"    {n}," for n in all_names)

    new_content = (
        header_doc + "\n"
        + "from __future__ import annotations\n\n"
        + funcs_part.strip() + "\n\n\n"
        + f"GENERATED_INPROC_TOOLS: list = [\n{list_lines}\n]\n"
    )
    _write(_TOOLS_GEN, new_content)


def _config_gen_parts(content: str) -> list[str]:
    """Extrait les entrées existantes du dict GENERATED_MCP_SERVERS."""
    m = re.search(r"GENERATED_MCP_SERVERS\s*[:\w\[\],\s]*=\s*\{(.*?)\}", content, re.DOTALL)
    if not m:
        return []
    raw = m.group(1).strip()
    # Normaliser l'indentation : chaque ligne devient "    <stripped>"
    lines = [f"    {l.strip()}" for l in raw.split("\n") if l.strip()]
    return lines


def _write_config_gen(name: str, port: int) -> None:
    existing = _read(_CONFIG_GEN)
    name_upper = name.upper().replace("-", "_")

    new_entry = (
        f'    "{name}": os.getenv("MCP_{name_upper}_URL", '
        f'f"http://{{MCP_HOST}}:{port}/mcp"),'
    )

    existing_lines = _config_gen_parts(existing)
    all_lines = existing_lines + [new_entry]
    entries_str = "\n".join(all_lines)

    new_content = (
        '"""Config MCP générée. Ne pas éditer manuellement — utilisez scripts/gen_mcp.py."""\n'
        "from __future__ import annotations\n"
        "import os\n\n"
        'MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1")\n\n'
        f"GENERATED_MCP_SERVERS: dict[str, str] = {{\n{entries_str}\n}}\n"
    )
    _write(_CONFIG_GEN, new_content)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Génère un serveur MCP complet avec l'IA Anthropic."
    )
    parser.add_argument("--name", required=True, help="Nom du serveur (kebab-case)")
    parser.add_argument("--description", required=True, help="Description de la source de données")
    parser.add_argument("--dry-run", action="store_true", help="Affiche sans écrire")
    args = parser.parse_args()

    print("[STEP:validate]")
    if not re.fullmatch(r"[a-z0-9-]+", args.name):
        print(f"Erreur : nom invalide '{args.name}'. Utilisez uniquement minuscules, chiffres et tirets.")
        return 1

    print("[STEP:find_port]")
    if args.name in _find_existing_names():
        print(f"Erreur : le serveur '{args.name}' existe déjà. Choisissez un nom différent.")
        return 1

    existing_ports = _find_existing_ports()
    next_port = max(existing_ports) + 1 if existing_ports else 9105
    camel   = _to_camel(args.name)
    py_name = _to_py(args.name)

    print(f"Génération du serveur MCP '{args.name}' (port {next_port})…")
    print(f"[PORT:{next_port}]")
    print("[STEP:build_prompt]")
    system_prompt = _build_system_prompt()
    print("[STEP:api_call]")
    raw = _call_api(system_prompt, args.name, args.description, camel, py_name)
    print("[STEP:parse]")
    blocks = _parse_blocks(raw)

    if len(blocks) < 3:
        print(
            f"Erreur : {len(blocks)}/3 blocs de code trouvés dans la réponse.\n"
            "Relancez ou utilisez --dry-run pour inspecter la réponse brute."
        )
        print("\n--- Réponse brute ---")
        print(raw[:1000])
        return 1

    mock_block   = blocks["MOCK_SOURCE"]
    server_block = blocks["MCP_SERVER"].replace("PLACEHOLDER_PORT", str(next_port))
    inproc_block = blocks["INPROC_TOOLS"]
    tool_names   = _extract_tool_names(inproc_block)

    if args.dry_run:
        print(f"\n=== PORT ALLOUÉ : {next_port} ===")
        print("\n--- [MOCK_SOURCE] ---")
        print(mock_block)
        print("\n--- [MCP_SERVER] ---")
        print(server_block)
        print("\n--- [INPROC_TOOLS] ---")
        print(inproc_block)
        print(f"\nOutils détectés : {tool_names}")
        return 0

    print("[STEP:write_mock]")
    print(f"  • mock_sources/_generated.py")
    _write_mock_gen(camel, mock_block)

    print("[STEP:write_servers]")
    print(f"  • mcp_servers/servers_generated.py")
    _write_servers_gen(args.name, next_port, camel, py_name, server_block)

    print("[STEP:write_tools]")
    print(f"  • runtime/tools_generated.py")
    _write_tools_gen(inproc_block, tool_names)

    print("[STEP:write_config]")
    print(f"  • runtime/config_generated.py")
    _write_config_gen(args.name, next_port)

    print(f"\n✓ Serveur '{args.name}' généré sur le port {next_port}.")
    print(f"  Outils : {', '.join(tool_names) or '(aucun détecté — vérifiez le fichier)'}")
    print(f"  → Lancez avec :    python -m mcp_servers {args.name}")
    print(f"  → Inproc dispo après : make up-inproc")
    return 0


if __name__ == "__main__":
    sys.exit(main())
