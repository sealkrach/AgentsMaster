# Registre sémantique (S1)

Le registre est la mémoire persistante du lab. Il stocke tous les MCPs générés,
leurs embeddings, leurs exécutions et les specs des connecteurs. Il évite de
régénérer ce qui existe déjà.

---

## Prérequis

```bash
# Docker doit être installé
make db-up          # démarre PostgreSQL 16 + pgvector (docker-compose)
make db-migrate     # applique la migration 001 (CREATE EXTENSION vector + tables)
```

Ajoutez dans `.env` :

```
DATABASE_URL=postgresql+asyncpg://lab:lab@localhost:5432/agentathon

# Embeddings — OPENAI_API_KEY est requis même si LAB_MODEL pointe vers Anthropic
OPENAI_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-small   # 1536 dimensions (défaut)
# EMBEDDING_BASE_URL=                    # vide = OpenAI public, sinon endpoint custom
```

Sans `DATABASE_URL`, tout fonctionne en mode dégradé (les endpoints `/registry` et
`/connectors` renvoient `{"items": [], "registry_enabled": false}`).

---

## Tables

### `mcps`

Stocke chaque MCP généré avec son vecteur d'embedding.

| Colonne | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `name` | text unique | Nom kebab-case |
| `description` | text | Description métier |
| `embedding` | vector(1536) | Embedding cosinus (text-embedding-3-small) |
| `mcp_code` | text | Bloc MCP_SERVER généré par le LLM |
| `version` | int | Incrémenté à chaque regénération |
| `quality_score` | float | Score composite (humain + heuristiques LLM) |
| `human_feedback_score` | float | Feedback humain (0–1) |
| `usage_count` | int | Nombre d'exécutions |
| `status` | enum | `sandbox` → `validated` → `promoted` → `deprecated` |
| `feedback` | jsonb | Historique des retours |

### `mcp_executions`

Trace chaque appel MCP pour le scoring et l'observabilité.

| Colonne | Type | Description |
|---|---|---|
| `mcp_id` | UUID FK | Lien vers `mcps` |
| `question` | text | Question posée à l'agent |
| `latency_ms` | int | Temps de réponse |
| `tokens_used` | int | Tokens consommés |
| `result_score` | float | Score de la réponse |
| `otel_trace_id` | text | Identifiant OTel pour le join avec SigNoz/ClickHouse |

### `connector_specs`

Descripteurs YAML des sources externes. Bootstrappés au démarrage depuis
`connector_specs/*.yaml`.

| Colonne | Type | Description |
|---|---|---|
| `name` | text unique | Identifiant court (`signoz`, `clickhouse`) |
| `kind` | text | `http_api` | `sql_http` | `grpc` |
| `spec_yaml` | text | YAML complet de la spec |
| `capabilities` | jsonb | `["traces", "metrics", "logs"]` |

---

## Recherche sémantique

```bash
curl "http://localhost:8080/registry/search?q=audit+des+accès+utilisateurs&limit=5"
```

Réponse :
```json
{
  "query": "audit des accès utilisateurs",
  "matches": [
    {
      "id": "…",
      "name": "audit-trail",
      "description": "Logs d'audit métier…",
      "version": 1,
      "score": 0.9234,
      "recommendation": "reuse"
    }
  ]
}
```

### Seuils (§4.3 du spec)

| Score cosinus | Recommandation | Action suggérée |
|---|---|---|
| ≥ 0.85 | `reuse` | Réutiliser le MCP existant |
| 0.70–0.85 | `propose` | Proposer à l'utilisateur, demander confirmation |
| < 0.70 | `generate` | Générer un nouveau MCP |

---

## Endpoints REST

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/registry` | Liste MCPs (`?offset=0&limit=50&status=validated`) |
| `GET` | `/registry/search` | Recherche cosinus (`?q=...&limit=5`) |
| `GET` | `/connectors` | Liste connector specs (`?capability=logs`) |
| `POST` | `/connectors` | Upsert connector spec |

---

## Flux de génération avec registre actif

```
POST /gen-mcp {name, description}
      │
      ├─ gen_mcp.py: validate + LLM call
      │
      ├─ [STEP:static_analysis] ──── violations? ──── REFUS (exit 1)
      │                                     ↓ OK
      ├─ [STEP:write_*]: écriture des 4 fichiers
      │
      ├─ [REGISTRY:json] ◄── intercepté par le endpoint, jamais affiché dans l'UI
      │
      └─ registry.save_mcp() ──► PostgreSQL (embedding généré si OPENAI_API_KEY présent)
                                  └─ SSE: {"type":"registry:saved","mcp_id":"..."}
```

---

## Analyse statique de sécurité

Chaque bloc de code généré est analysé avant écriture. Les violations bloquent
immédiatement la génération.

| Règle | Raison |
|---|---|
| SQL `INSERT/UPDATE/DELETE/DROP/ALTER/TRUNCATE/CREATE` | Sources READ-ONLY uniquement |
| Méthodes HTTP `POST/PUT/PATCH/DELETE` | Interdit d'écrire via MCP |
| `subprocess`, `os.system`, `os.popen` | Pas d'exécution de commandes système |
| `eval`, `exec` | Pas d'exécution de code dynamique |
| Écriture fichier (mode `w/a/x`) hors `/tmp` | Sandbox filesystem |

```bash
# Test direct de l'analyseur :
python3 -c "
from scripts.static_analysis import analyze
code = 'import os; os.system(\"rm -rf /\")'
safe, violations = analyze(code)
print(safe, violations)
"
```

---

## Connector specs

Les fichiers `connector_specs/*.yaml` sont chargés au démarrage et insérés en
base (upsert idempotent). Ils décrivent comment un MCP peut atteindre une source
externe tout en respectant les contraintes de sandbox.

Deux specs livrées :

| Nom | Kind | Capacités |
|---|---|---|
| `signoz` | `http_api` | `traces`, `metrics`, `logs`, `alerts` |
| `clickhouse` | `sql_http` | `analytics`, `traces_storage`, `metrics_storage`, `logs_storage` |

Pour ajouter une source :

```yaml
# connector_specs/ma-source.yaml
name: ma-source
kind: http_api
capabilities: [contrats, clients]
endpoints:
  base_url: "${MA_SOURCE_URL}"
  auth:
    type: api_key
    header: X-Api-Key
    secret_env: MA_SOURCE_API_KEY
security:
  read_only: true
  allowed_methods: [GET, HEAD]
```

---

## Migrations

```bash
# Appliquer
make db-migrate          # = alembic upgrade head

# Créer une nouvelle migration
alembic revision --autogenerate -m "add scoring columns"
```

La migration `001` :
1. `CREATE EXTENSION IF NOT EXISTS vector`
2. Tables `mcps`, `mcp_executions`, `connector_specs`
3. Index IVFFLAT cosinus sur `mcps.embedding` (listes = 10)

---

## Commandes utiles

```bash
make db-up              # démarrer PostgreSQL
make db-down            # arrêter
make db-migrate         # appliquer migrations
make db-shell           # ouvrir psql

# Vérifier le registre depuis psql
SELECT name, version, status, quality_score FROM mcps;
SELECT name, capabilities FROM connector_specs;
```
