"""Catalogue MCP gouverné de l'IDP platform (P1).

Quatre serveurs MCP RÉELS, contrats IDENTIQUES à ceux du kit agentathon
(mêmes noms d'outils + signatures), mais branchés sur les vrais moteurs :
  - relational + documents -> PostgreSQL (asyncpg, lecture seule)
  - vector                 -> Qdrant (qdrant-client)
  - graph                  -> ArangoDB (python-arango)

=> Un skill écrit contre le kit se transfère ICI sans aucun re-travail :
   seul ce qu'il y a derrière le serveur MCP change.

Destiné à vivre dans le repo IDP (ex: backend/idp_mcp/).
"""
