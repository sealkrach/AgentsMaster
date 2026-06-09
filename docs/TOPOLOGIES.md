# Sources mockées, couche MCP & topologies d'agents

Ce document explique le « paysage » reproduit dans le lab et comment l'orchestration
est câblée. Principe directeur : **le contrat MCP est fidèle à la prod ; seuls les
moteurs derrière sont mockés.** Un skill écrit ici se transfère sans re-travail.

## 1. Le paysage de données (mock, mais comportement réel)

Quatre sources, toutes embarquées dans le process (zéro service stateful à gérer) :

| Source        | Moteur mock              | Comportement | Équivalent prod |
|---------------|--------------------------|--------------|-----------------|
| Relationnel   | SQLite en mémoire        | vrai SQL (jointures, agrégats) | PostgreSQL |
| Vectoriel     | TF-IDF + cosinus (maison)| vrai ranking par similarité, hors-ligne | Qdrant + embeddings denses |
| Graphe        | networkx                 | vraies traversées (voisinage, plus court chemin) | ArangoDB |
| Corpus        | dict en mémoire          | recherche plein-texte | object store / DMS |

Les données vivent dans `data/synthetic/landscape.json` (documents, chunks,
entités, relations, jobs). C'est un **jeu synthétique** : aucune donnée réelle.

Le graphe relie fournisseurs, factures, contrats, services et personnes
(relations `ISSUED`, `SIGNED`, `UNDER_CONTRACT`, `COVERS`, `WORKS_FOR`, `SAME_AS`),
ce qui permet de démontrer un vrai **GraphRAG** (skill `entity-dossier`).

### Pourquoi des moteurs embarqués plutôt que de vrais Qdrant/Arango ?
Parce que ce qui doit être fidèle pour le zéro-rework, c'est le **contrat des outils
MCP**, pas le moteur. On a donc du comportement réel (vrai SQL, vrai cosinus, vraies
traversées) sans aucun service séparé à provisionner/seeder/détruire par namespace.
Passer plus tard à de vrais moteurs (pour apprendre l'AQL, ou load-tester) ne change
**que ce qu'il y a derrière le serveur MCP** — aucun skill à retoucher.

## 2. La couche MCP (fidèle à la prod)

Quatre **vrais serveurs MCP** (FastMCP, transport `streamable-http`), un par source :

| Serveur     | Port  | Outils exposés |
|-------------|-------|----------------|
| documents   | 9101  | `search_documents`, `get_document` |
| relational  | 9102  | `sql_query`, `lookup_supplier`, `list_jobs` |
| vector      | 9103  | `vector_search` |
| graph       | 9104  | `find_entity`, `graph_neighbors`, `graph_path` |

Le runtime les charge via `MultiServerMCPClient` (langchain-mcp-adapters). L'agent voit
donc exactement la topologie « tools = MCP » de la production.

Deux modes (même contrat) :
- **`MCP_MODE=mcp`** (défaut) — vrais serveurs MCP. `make mcp` les lance tous.
- **`MCP_MODE=inproc`** — outils locaux équivalents, un seul process (laptop/CI).
  `make up-inproc`.

En OpenShift : chaque serveur MCP est un Deployment+Service (`deploy/openshift/
mcp-servers.yaml`), le runtime les joint par DNS interne. La NetworkPolicy
`allow-intra-mcp` ouvre uniquement les ports MCP, à l'intérieur du namespace.

## 3. Les trois topologies d'agents

On ne change que l'orchestration ; outils et skills sont les mêmes. Sélection par
`LAB_TOPOLOGY`. Toutes reposent sur DeepAgents/LangGraph (le runtime = commodity).

### `single` (défaut) — un agent, tous les outils
Le plus direct. Un agent unique avec accès à tous les outils MCP et tous les skills
(progressive disclosure : un skill n'est chargé que si sa `description` matche).
À privilégier pour démarrer et pour 90 % des cas.

### `supervisor` — délégation hiérarchique
Un agent chef délègue à deux subagents spécialisés :
- **retriever** : outils de contexte (vecteur, graphe, corpus) ;
- **decider** : outils relationnels (fournisseur, jobs, SQL) + décision.
Utile quand la tâche se décompose proprement (récupérer ↔ statuer) et qu'on veut
des sous-contextes isolés. Natif DeepAgents (`subagents=[…]`).

### `swarm` — pairs avec handoff *(template avancé, à affiner)*
Deux agents pairs (`triage`, `research`) qui se passent la main via des outils de
handoff (`handoff_to_research` / `handoff_to_triage`), câblés dans un `StateGraph`
LangGraph avec routage `Command(goto=…, graph=PARENT)`.

> ⚠ **Honnêteté** : le graphe se construit et se compile, mais le comportement de
> handoff dépend du modèle et **demande du réglage de prompts** (quand passer la main,
> comment éviter les allers-retours). Traitez `swarm` comme un point de départ
> pédagogique, pas comme un défaut de production. HITL non câblé sur les pairs swarm.

## 4. Où ça se branche en prod (rappel)
- Moteurs mock → vrais Postgres / Qdrant / ArangoDB **derrière les mêmes serveurs MCP**.
- `MemorySaver` → checkpointer persistant (Postgres).
- Outils MCP → vos vrais serveurs MCP gouvernés.
- Traces → LangSmith / Arize Phoenix (l'agent est un graphe LangGraph, donc traçable).
- Le **skill**, lui, ne bouge pas : c'est ça le contrat.
