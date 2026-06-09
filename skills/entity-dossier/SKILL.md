---
name: entity-dossier
description: >
  Construit le dossier complet d'une entité (fournisseur, contrat) en combinant
  le graphe de connaissances, la recherche sémantique et les faits relationnels —
  c'est un cas de GraphRAG. Use when l'utilisateur demande un « dossier », un
  « 360 », « tout ce qu'on a sur <entité> », les liens/relations d'un fournisseur
  ou d'un contrat, ou « à quoi est rattachée » une facture. Do NOT use pour un
  simple contrôle de facture (utiliser invoice-triage).
license: MIT
allowed-tools: find_entity, graph_neighbors, graph_path, vector_search, lookup_supplier, sql_query, get_document
metadata:
  author: lab.example
  version: "1.0"
---

# entity-dossier (GraphRAG)

## Objectif
Donner une vue 360 d'une entité en croisant les trois sources mockées, exactement
comme le ferait la plateforme en prod (le contrat des outils est identique).

## Quand l'utiliser
- Demande de dossier / 360 / « tout ce qu'on a sur X » / liens d'un fournisseur ou contrat.
- NE PAS utiliser pour un simple contrôle de facture.

## Instructions

1. **Localiser l'entité** avec `find_entity(name)`. Si plusieurs candidats, choisis
   le plus pertinent (préfère un `supplier:` ou `contract:`) et note son `id`.

2. **Explorer le graphe** avec `graph_neighbors(entity_id)` : récupère les relations
   (factures émises, contrats signés, services couverts, entités liées). Au besoin,
   `graph_path(a, b)` pour expliquer un lien indirect.

3. **Enrichir sémantiquement** avec `vector_search(<nom + termes clés>, top_k=3)` :
   récupère les passages documentaires pertinents (le « RAG »).

4. **Vérifier les faits** avec `lookup_supplier(name)` (statut, conditions) et,
   si utile, `sql_query("SELECT … FROM documents WHERE issuer LIKE …")` pour les
   montants/dates. `get_document(id)` pour citer un document précis.

5. **Synthétiser le dossier.**

## Format de sortie attendu
Un dossier structuré :
- **Entité** : nom, type, statut, conditions.
- **Graphe** : liste des relations (rel → entité cible) en une ligne chacune.
- **Documents liés** : passages pertinents avec leur `doc_id`.
- **Faits relationnels** : montants, dates, jobs en cours.
- **Synthèse** : 2-3 phrases, en citant les identifiants. Signale tout point d'attention
  (ex : fournisseur inactif, job en erreur, contrat arrivant à échéance).

## Exemple d'amorce
« Fais-moi le dossier du fournisseur Acme » → find_entity('Acme') → graph_neighbors
('supplier:acme') → vector_search('Acme hébergement contrat') → lookup_supplier('Acme').
