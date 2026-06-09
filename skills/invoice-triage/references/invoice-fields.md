# Référentiel — champs facture & règles de contrôle

> Ce fichier n'est lu par l'agent que **lorsque le skill `invoice-triage`
> l'invoque** (progressive disclosure). Il n'encombre pas le contexte par défaut.

## Champs à extraire

| Champ | Clé attendue | Obligatoire |
|---|---|---|
| Émetteur | `issuer` | oui |
| Numéro de facture | `invoice_number` | oui |
| Date | `date` (YYYY-MM-DD) | oui |
| Montant HT | `amount_ht` | oui |
| TVA | `vat` | oui |
| Montant TTC | `amount_ttc` | oui |
| Devise | `currency` | oui |
| Bon de commande | `po_number` | non |

## Règles de contrôle
1. **Cohérence montant** : `amount_ht + vat == amount_ttc` (tolérance ± 0,01).
2. **Devise** : `EUR` attendue ; toute autre devise → écart à signaler.
3. **Date** : ne doit pas être postérieure à la date du jour.
4. **PO** : si `po_number` présent, le mentionner ; absence non bloquante.

## Seuils d'escalade
- Montant TTC **> 10 000 EUR** → `À ESCALADER` (double validation requise).
- Fournisseur **inconnu** au CRM ou **statut ≠ actif** → `À ESCALADER`.

## Décision — logique
```
si incohérence_bloquante:        REJETER
sinon si escalade_requise:       ESCALADER
sinon:                           PAYER
```
