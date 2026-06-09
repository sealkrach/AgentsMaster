---
name: invoice-triage
description: >
  Trie et valide les factures fournisseurs entrantes : extraction des champs
  clés, contrôle de cohérence, rapprochement avec le fournisseur au CRM, et
  décision motivée (à payer / à rejeter / à escalader). Use when l'utilisateur
  mentionne une facture, un numéro de facture (ex INV-...), un avoir, un montant
  TTC/HT, un fournisseur, ou demande de vérifier, contrôler ou rapprocher une
  facture. Do NOT use pour des courriers RH, des contrats, ou des documents non
  comptables.
license: MIT
allowed-tools: search_documents, get_document, lookup_supplier
metadata:
  author: lab.example
  version: "1.0"
---

# invoice-triage

## Objectif
Permettre à un gestionnaire comptable de trier une facture entrante en quelques
secondes, avec une décision motivée et traçable, sur le corpus du bac à sable.

## Quand l'utiliser
- L'utilisateur fournit un identifiant de facture, un nom de fournisseur, ou
  demande de « vérifier / contrôler / rapprocher » une facture.
- NE PAS utiliser pour des documents non comptables.

## Instructions

1. **Récupérer la facture.** Si un `doc_id` est donné, utilise `get_document`.
   Sinon, utilise `search_documents` avec le mot-clé fourni (fournisseur,
   numéro, montant) puis sélectionne la facture pertinente.

2. **Extraire les champs clés** (voir `references/invoice-fields.md` pour la
   liste exacte et les règles) : émetteur, numéro, date, montant HT, TVA,
   montant TTC, devise, n° de bon de commande s'il existe.

3. **Contrôles de cohérence :**
   - HT + TVA = TTC (tolérance 0,01) ;
   - la devise est attendue (EUR) ;
   - la date n'est pas dans le futur.
   Note tout écart.

4. **Rapprochement fournisseur.** Utilise `lookup_supplier` sur l'émetteur.
   Vérifie que le fournisseur est connu et **actif**, et récupère ses
   conditions de paiement.

5. **Décision :**
   - `À PAYER` si tous les contrôles passent et le fournisseur est actif ;
   - `À REJETER` si incohérence bloquante (ex TTC faux) ;
   - `À ESCALADER` si fournisseur inconnu/inactif ou montant > 10 000 EUR.

6. **Point de validation.** Présente le récapitulatif et la décision, puis
   **attends l'accord de l'utilisateur** avant d'écrire quoi que ce soit.

## Format de sortie attendu
Un tableau récapitulatif (champ → valeur), la liste des contrôles (✓/✗), le
statut du fournisseur, puis une ligne **Décision : <…>** suivie d'une
justification d'une phrase citant les `doc_id` et identifiants utilisés.

## Références
- `references/invoice-fields.md` — champs à extraire, règles de contrôle, et
  seuils d'escalade. À consulter à l'étape 2 et 5.
