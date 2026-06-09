"""Source GRAPHE mock — vrai graphe networkx (entités/relations), vraies traversées.

Comportement de graphe réel (voisinage, plus court chemin), sans service séparé.
En prod, on remplace par le vrai ArangoDB : le contrat MCP (graph_neighbors,
graph_path, find_entity) reste identique, donc aucun skill à retoucher.
"""
from __future__ import annotations

from typing import Any

import networkx as nx


class GraphSource:
    def __init__(self, data: dict[str, Any]) -> None:
        self.g = nx.DiGraph()
        for e in data.get("entities", []):
            self.g.add_node(e["id"], **{k: v for k, v in e.items() if k != "id"})
        for r in data.get("relations", []):
            self.g.add_edge(r["from"], r["to"], rel=r["rel"])

    def find_entity(self, name: str) -> list[dict]:
        """Trouve des entités par nom (sous-chaîne, insensible à la casse)."""
        n = name.lower().strip()
        out = []
        for node, attrs in self.g.nodes(data=True):
            if n in str(attrs.get("name", "")).lower() or n in node.lower():
                out.append({"id": node, **attrs})
        return out

    def neighbors(self, entity_id: str) -> dict:
        """Voisinage direct (relations entrantes et sortantes) d'une entité."""
        if entity_id not in self.g:
            return {"error": f"Entité inconnue : {entity_id}"}
        out_edges = [{"rel": d["rel"], "direction": "out", "node": v,
                      "name": self.g.nodes[v].get("name", v)}
                     for _, v, d in self.g.out_edges(entity_id, data=True)]
        in_edges = [{"rel": d["rel"], "direction": "in", "node": u,
                     "name": self.g.nodes[u].get("name", u)}
                    for u, _, d in self.g.in_edges(entity_id, data=True)]
        return {"entity": entity_id, "attributes": dict(self.g.nodes[entity_id]),
                "edges": out_edges + in_edges}

    def path(self, src: str, dst: str) -> list[str] | dict:
        """Plus court chemin entre deux entités (graphe non orienté pour la connexité)."""
        try:
            return nx.shortest_path(self.g.to_undirected(as_view=True), src, dst)
        except (nx.NetworkXNoPath, nx.NodeNotFound) as exc:
            return {"error": str(exc)}
