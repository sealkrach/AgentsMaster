# Agentathon Lab — kit clef en main

Un environnement **prêt à l'emploi** pour faire concevoir des agents par le plus
grand nombre, en une journée, dans un cadre **gouverné** adapté à un contexte
régulé (banque/assurance).

Le principe : on ne construit pas une plateforme, on **livre des skills**. Le
runtime est un *commodity* (DeepAgents sur LangGraph) ; ce que les participants
produisent, ce sont des **skills** au format ouvert [agentskills.io](https://agentskills.io) —
réutilisables ensuite tels quels dans la vraie plateforme.

## Ce que ça fait

- Un **runtime DeepAgents/LangGraph** exposé en FastAPI (`/invoke`, `/stream`, `/health`).
- **Quatre sources de données mockées à comportement réel**, embarquées (zéro service
  à gérer) : relationnel **SQLite** (vrai SQL), vectoriel **TF-IDF/cosinus** (hors-ligne),
  graphe **networkx** (vraies traversées), corpus documentaire.
- **Quatre vrais serveurs MCP** devant ces sources → l'agent voit la topologie
  « tools = MCP » **identique à la prod** ; seuls les moteurs derrière sont mockés.
- **Trois topologies d'agent** prêtes à forker : `single`, `supervisor` (subagents),
  `swarm` (handoff). Sélection par `LAB_TOPOLOGY`.
- **Génération IA de skills et serveurs MCP** depuis une description en langage naturel
  (multi-provider : Anthropic, OpenAI, tout endpoint compatible OpenAI).
- **Registre sémantique** (S1) : PostgreSQL + pgvector — recherche cosinus, déduplication
  automatique, versionnement, seuils reuse/propose/generate.
- **Analyse statique de sécurité** sur tout code MCP généré (rejet SQL destructeur,
  HTTP write, subprocess, eval/exec).
- **Connector specs** : descripteurs YAML de sources externes (SigNoz, ClickHouse…)
  avec règles de sandboxing k3s.
- **Panneau paramètres ⚙** dans l'UI : configuration live de tous les paramètres
  runtime (LLM, topologie, observabilité) écrits dans `.env`.
- Les **skills chargés depuis ce repo** (`FilesystemBackend`) → revue PR + CI = gouvernance.
- **Progressive disclosure** : au démarrage l'agent ne voit que `name`+`description` ;
  le `SKILL.md` complet n'est lu que quand la tâche matche.
- **Human-in-the-loop** (`interrupt_on`) : validation avant toute écriture.
- **Données 100 % synthétiques** → zéro gate de conformité pour participer.
- Un **scaffold de skill**, un **harnais d'eval**, une **UI de chat**.
- Le **provisioning OpenShift** de namespaces éphémères isolés (TTL + auto-teardown).

➜ Topologies : [`docs/TOPOLOGIES.md`](docs/TOPOLOGIES.md) — Génération IA : [`docs/GEN.md`](docs/GEN.md) — Registre : [`docs/REGISTRY.md`](docs/REGISTRY.md)

---

## Démarrage rapide (local, sans registre)

Le plus simple — un seul process, aucune base de données :

```bash
cp .env.example .env          # renseignez LAB_MODEL + la clé provider
make install
make up-inproc                 # http://localhost:8080  (MCP_MODE=inproc)
```

Dans l'UI, tapez : `contrôle la facture INV-2026-0044` ou `fais-moi le dossier du fournisseur Acme`.

## Avec le registre sémantique (S1)

Active la recherche cosinus, la déduplication et la sauvegarde des MCPs générés :

```bash
make db-up          # démarre PostgreSQL+pgvector (Docker)
make db-migrate     # crée les tables (une seule fois)
# Ajoutez dans .env :
# DATABASE_URL=postgresql+asyncpg://lab:lab@localhost:5432/agentathon
# OPENAI_API_KEY=sk-...   (pour les embeddings, indépendant de LAB_MODEL)
make up-inproc
```

## Topologie MCP complète (deux terminaux)

```bash
make mcp                       # terminal 1 : les 4 serveurs MCP
make up                        # terminal 2 : le runtime (MCP_MODE=mcp)
```

Changer de topologie : `LAB_TOPOLOGY=supervisor make up-inproc` (ou `swarm`).

## Générer un skill ou un MCP par l'IA

```bash
make gen-skill name=contrat-renouvellement description="Vérifie les contrats arrivant à échéance"
make gen-mcp   name=audit-trail description="Logs d'audit : acteur, date, type d'action"
```

Ou depuis l'UI : panneau **Créer un élément** (onglets Skill / Serveur MCP).

## Changer de provider LLM

```bash
# .env — choisissez UN bloc :
LAB_MODEL=anthropic:claude-sonnet-4-6 + ANTHROPIC_API_KEY=sk-ant-...
# LAB_MODEL=openai:gpt-4o + OPENAI_API_KEY=sk-...
# LAB_MODEL=openai:llama3 + OPENAI_API_KEY=ollama + OPENAI_BASE_URL=http://localhost:11434/v1
```

## Lab de l'événement (OpenShift, namespaces éphémères)

```bash
TTL_HOURS=48 ./scripts/provision_namespace.sh equipe-alpha
```

Détails : [`deploy/openshift/README.md`](deploy/openshift/README.md).

---

## Carte du repo

```
runtime/           # FastAPI + assemblage DeepAgents + topologies
  embeddings.py    #   embeddings OpenAI (1536d) pour le registre
  registry.py      #   CRUD sémantique : save_mcp, semantic_search
db/                # Modèles SQLAlchemy (mcps, mcp_executions, connector_specs)
alembic/           # Migrations PostgreSQL (001 : pgvector + tables)
mock_sources/      # 4 moteurs mock : SQLite, cosinus, networkx, corpus
mcp_servers/       # 4 vrais serveurs MCP (FastMCP)
connector_specs/   # Specs YAML read-only : signoz, clickhouse (bootstrap S1)
skills/            # SKILL.md exemples : invoice-triage, entity-dossier (GraphRAG)
scripts/
  gen_skill.py     #   génération IA de SKILL.md
  gen_mcp.py       #   génération IA de serveur MCP + analyse statique
  static_analysis.py #  rejet SQL/HTTP write/eval/exec
data/synthetic/    # landscape.json : docs, chunks, entités, relations
ui/                # UI de chat + panneau ⚙ paramètres
eval/              # jeu de cas + runner async
deploy/openshift/  # namespace éphémère + runtime + mcp-servers + reaper
docs/              # FACILITATOR.md, PARTICIPANT.md, TOPOLOGIES.md, GEN.md, REGISTRY.md
```

---

## Pour les organisateurs / participants

- Organiser l'événement : [`docs/FACILITATOR.md`](docs/FACILITATOR.md)
- Construire un skill : [`docs/PARTICIPANT.md`](docs/PARTICIPANT.md)
- Génération IA (skills + MCPs) : [`docs/GEN.md`](docs/GEN.md)
- Registre sémantique : [`docs/REGISTRY.md`](docs/REGISTRY.md)

---

## Notes d'honnêteté

- **Squelette, pas produit fini.** À adapter à votre socle. Faites-le passer par
  votre revue sécurité avant tout usage réel.
- **DeepAgents évolue vite** : épinglez les versions (`pip freeze`) avant l'événement.
- **Exécution de scripts dans les skills** : le kit ne dépend pas d'un sandbox
  backend. Sur OpenShift, sandboxez l'exécution (gVisor/Kata) si vous l'activez.
- **Égress** : restreignez la NetworkPolicy au seul endpoint modèle approuvé.
- **Modèle** : pointez `LAB_MODEL` vers votre endpoint approuvé (Bedrock/Azure),
  idéalement en auth par rôle plutôt qu'une clé en clair.
