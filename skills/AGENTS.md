# Conventions du lab agentathon

Ce fichier est **toujours chargé** dans le contexte de l'agent (mémoire), à la
différence des skills qui sont lus à la demande. Garde-le court.

## Bac à sable
- Tu travailles **uniquement sur des données synthétiques** (corpus factice).
  Ne prétends jamais accéder à des systèmes ou des données de production.
- Le répertoire de travail est ce repo. Les fichiers que tu écris vont sous `./workspace/`.

## Outils disponibles
- `search_documents(query)` — cherche dans le corpus documentaire factice.
- `get_document(doc_id)` — récupère un document complet.
- `lookup_supplier(name)` — recherche un fournisseur dans le CRM factice.

## Règles
- Quand une tâche correspond à la description d'un skill, **lis le SKILL.md complet
  puis suis-le** étape par étape.
- Avant toute écriture de fichier ou action irréversible, **demande validation**
  (un point d'interruption est prévu pour ça).
- Si aucun skill ne correspond, réponds directement avec tes outils, sobrement.
- Cite toujours les `doc_id` et les identifiants exacts sur lesquels tu t'appuies.
