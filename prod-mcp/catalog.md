# Catalogue d'outils MCP gouvernés — IDP platform (P1)

**Posture : LECTURE SEULE.** Aucun outil ne modifie ni ne supprime de donnée. Toute
écriture future devra passer par un HITL (`interrupt`) côté runtime — jamais ici.
La vraie garantie SQL est un **rôle Postgres en lecture seule** (`GRANT SELECT`) ;
la garde applicative (`sqlguard`) n'est qu'une défense en profondeur.

| Outil | Serveur (port) | Backend | Entrée → Sortie | Sensibilité | Notes de gouvernance |
|---|---|---|---|---|---|
| `search_documents` | documents (9101) | PostgreSQL | `query:str` → `list[dict]` | 🟠 confidentiel | full-text/ILIKE, plafonné à `ROW_CAP` |
| `get_document` | documents (9101) | PostgreSQL | `doc_id:str` → `dict\|None` | 🟠 confidentiel | clé exacte, 1 ligne |
| `sql_query` | relational (9102) | PostgreSQL | `sql:str` → `list[dict]` | 🟠 confidentiel | SELECT/WITH uniquement (garde + rôle RO), timeout + plafond |
| `lookup_supplier` | relational (9102) | PostgreSQL | `name:str` → `dict\|None` | 🟡 interne | requête paramétrée |
| `list_jobs` | relational (9102) | PostgreSQL | `status:str?` → `list[dict]` | 🟢 interne | paramétré, plafonné |
| `vector_search` | vector (9103) | Qdrant | `query:str, top_k:int=3` → `list[dict]` | 🟠 confidentiel | embedding DOIT matcher l'index |
| `find_entity` | graph (9104) | ArangoDB | `name:str` → `list[dict]` | 🟡 interne | AQL paramétré (valeurs en bind_vars) |
| `graph_neighbors` | graph (9104) | ArangoDB | `entity_id:str` → `dict` | 🟡 interne | traversée 1-hop |
| `graph_path` | graph (9104) | ArangoDB | `src:str, dst:str` → `list\|dict` | 🟡 interne | plus court chemin |

**Owner :** Paris tech (catalogue) · révisions : CISO (égress, secrets, PII), CTO.
**Garde-fous transverses :** secrets via store/role-auth (jamais en clair), égress
restreint aux seuls Postgres/Arango/Qdrant + endpoint d'embedding, plafond de lignes,
timeout d'instruction, traçage automatique quand exécuté derrière le runtime DeepAgents.
