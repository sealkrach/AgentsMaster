# Catalogue MCP de production (P1)

Implémente le **catalogue d'outils MCP gouverné** de la plateforme IDP. Mêmes contrats
que les serveurs mock du kit (`mcp_servers/`) — **mêmes noms d'outils, mêmes signatures** —
mais branchés sur les vrais moteurs. Un skill écrit au hackathon se transfère ici **sans
re-travail** : seul ce qu'il y a derrière le serveur MCP change.

> Destiné à vivre dans le repo IDP (ex : `backend/idp_mcp/`). Il est livré ici, à côté du
> kit, pour que la **parité des contrats** soit vérifiable automatiquement (voir tests).

## Ce qui est branché
| Serveur (port) | Backend réel | Driver |
|---|---|---|
| documents (9101) | PostgreSQL | asyncpg (lecture seule) |
| relational (9102) | PostgreSQL | asyncpg (lecture seule) |
| vector (9103) | Qdrant | qdrant-client (async) |
| graph (9104) | ArangoDB | python-arango |

## Gouvernance (dans le code)
- **Lecture seule** : aucun outil destructif. Écriture future = HITL `interrupt` côté runtime.
- **SQL** : `sqlguard` n'autorise qu'un `SELECT`/`WITH` unique ; transaction `readonly` ;
  timeout + plafond de lignes. **La vraie garantie est un rôle Postgres `GRANT SELECT`.**
- **Valeurs paramétrées** partout ($1 / bind_vars) ; identifiants de schéma issus de l'env (validés), jamais de l'agent.

## Configuration (env)
```
# PostgreSQL — utilisez un rôle EN LECTURE SEULE
IDP_PG_DSN=postgresql://idp_ro@pg-host:5432/idp
IDP_PG_STATEMENT_TIMEOUT_S=5
IDP_ROW_CAP=200
# ArangoDB
IDP_ARANGO_URL=http://arango:8529
IDP_ARANGO_DB=idp
IDP_ARANGO_USER=idp_ro
IDP_ARANGO_PASSWORD=...        # idéalement via secret store / role-auth
# Qdrant
IDP_QDRANT_URL=http://qdrant:6333
IDP_QDRANT_COLLECTION=documents
# Embedding — DOIT matcher le modèle qui a indexé Qdrant
IDP_EMBEDDING_PROVIDER=http
IDP_EMBEDDING_ENDPOINT=https://<endpoint-embedding-approuvé>/embeddings
IDP_EMBEDDING_MODEL=<même-modèle-que-l-index>
# Mapping de schéma (si différent des défauts)
IDP_T_DOCUMENTS=documents
IDP_C_DOC_ID=doc_id
# ... voir config.py pour la liste complète
```

## Lancer
```bash
pip install -r requirements.txt
python -m idp_mcp documents     # un serveur
python -m idp_mcp all           # les quatre
```

## Déployer
Réutilisez les manifests du kit (`deploy/helm/` ou `deploy/openshift/`) en changeant
deux choses : (1) l'**image** (celle qui embarque `idp_mcp` au lieu de `mcp_servers`) et
la **commande** `python -m idp_mcp <name>` ; (2) ajoutez les **connexions DB** via un
Secret (DSN Postgres en lecture seule, creds Arango/Qdrant, endpoint d'embedding) et
**restreignez l'égress** à ces seules destinations.

## Validation — ce qui est prouvé ICI, et ce qui reste votre pré-flight
Prouvé hors-ligne (voir `tests/`) :
- **Parité des contrats** avec le kit (mêmes outils + signatures) → `python tests/test_parity.py`
- **Garde SQL** lecture seule → `python tests/test_sqlguard.py`
- Compilation de tout le package.

**Pas prouvé ici (pas d'accès aux vraies bases dans cet environnement) — votre pré-flight :**
1. Brancher sur une **réplique de staging en lecture seule** et appeler chaque outil.
2. Confirmer que `IDP_EMBEDDING_MODEL` est **exactement** le modèle ayant indexé Qdrant
   (même dimension) — sinon `vector_search` renvoie du bruit.
3. Vérifier le rôle Postgres en lecture seule (tenter un `INSERT` doit échouer côté DB).
4. Mapper `config.py` à votre schéma réel (noms de tables/colonnes/collections).
