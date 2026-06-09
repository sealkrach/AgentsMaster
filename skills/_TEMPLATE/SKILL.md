---
name: REPLACE-WITH-skill-name
description: >
  EN UNE OU DEUX PHRASES, dis QUOI fait ce skill et SURTOUT QUAND l'utiliser.
  C'est LE texte le plus important : c'est sur cette description seule que
  l'agent décide d'activer (ou non) le skill. Sois spécifique, riche en
  mots-clés, et mentionne les formulations réelles des utilisateurs.
  Termine par un "Use when..." et un "Do NOT use when..." explicites.
  Exemple : "Trie et valide les factures fournisseurs entrantes. Use when
  l'utilisateur parle de facture, d'avoir, de bon de commande, ou demande de
  vérifier/rapprocher une facture. Do NOT use pour des courriers RH ou des
  contrats."
# Champs optionnels (spec agentskills.io) :
# license: MIT
# allowed-tools: search_documents, get_document, lookup_supplier
# metadata:
#   author: prenom.nom
#   version: "0.1"
---

# REPLACE-WITH-skill-name

## Objectif
Une phrase : le problème métier que ce skill résout, et pour qui.

## Quand l'utiliser
- Décris les cas où ce skill s'applique.
- Et les cas où il NE s'applique PAS.

## Instructions
Étapes numérotées et déterministes. Nomme les outils explicitement.

1. ...
2. ...
3. **Point de validation** : avant toute écriture/action, présente le résultat
   à l'utilisateur et attends son accord.

## Format de sortie attendu
Décris la forme du résultat (ex : un tableau récapitulatif + une décision
"à payer / à rejeter / à escalader" + la justification).

## Références (optionnel)
- `references/mon-doc.md` — ce qu'il contient et quand le consulter.
