"""Prouve que le catalogue de PROD expose EXACTEMENT les mêmes outils MCP que le kit
(mêmes noms + mêmes paramètres). C'est la garantie « zéro re-travail » pour les skills.
Dépendance-zéro : on parse les sources en AST, on n'importe rien."""
from __future__ import annotations

import ast
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
KIT = ROOT / "mcp_servers" / "servers.py"
PROD = ROOT / "prod-mcp" / "idp_mcp" / "servers.py"


def _tools(path: pathlib.Path) -> dict[str, list[str]]:
    tree = ast.parse(path.read_text())
    out: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            is_tool = any(
                isinstance(d, ast.Call)
                and isinstance(d.func, ast.Attribute)
                and d.func.attr == "tool"
                for d in node.decorator_list
            )
            if is_tool:
                out[node.name] = [a.arg for a in node.args.args]
    return out


def main() -> int:
    kit, prod = _tools(KIT), _tools(PROD)
    ok = kit == prod
    print("Outils KIT :", {k: kit[k] for k in sorted(kit)})
    print("Outils PROD:", {k: prod[k] for k in sorted(prod)})
    if ok:
        print(f"\n✅ PARITÉ OK — {len(kit)} outils, mêmes noms et mêmes signatures.")
        return 0
    print("\n❌ DIVERGENCE :")
    print("  manquants en prod :", set(kit) - set(prod))
    print("  en trop en prod  :", set(prod) - set(kit))
    for name in set(kit) & set(prod):
        if kit[name] != prod[name]:
            print(f"  signature diff {name}: kit={kit[name]} prod={prod[name]}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
