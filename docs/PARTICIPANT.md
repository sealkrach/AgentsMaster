# Guide participant — construis ton premier agent en une journée

Pas besoin d'être développeur. Un agent utile, ici, c'est surtout un **skill** :
un dossier qui dit à l'agent *quoi faire* et *quand*.

## 1. Ton environnement
Ton équipe a un lab déjà provisionné (une URL fournie par les facilitateurs).
Tu y trouves une UI de chat. Tape une demande pour voir l'agent travailler —
tu verras en direct quel skill il charge et quels outils il appelle.

Essaie : `contrôle la facture INV-2026-0044`.

## 2. Crée ton skill
```bash
make new-skill name=mon-skill        # ou : ./scripts/new_skill.sh mon-skill
```
Ça crée `skills/mon-skill/SKILL.md` à partir du template.

## 3. Écris-le (l'ordre compte)
1. **La `description`** — c'est LE texte critique. L'agent décide d'activer ton
   skill **sur cette seule description**. Donc :
   - sois spécifique et riche en mots-clés ;
   - mentionne les formulations réelles des utilisateurs ;
   - termine par un **« Use when… »** et un **« Do NOT use when… »**.
2. **Les instructions** — des étapes numérotées, déterministes, qui nomment les
   outils (`search_documents`, `get_document`, `lookup_supplier`).
3. **Un point de validation** — avant toute écriture/action, fais présenter le
   résultat et attends l'accord. (Le lab intercepte déjà les écritures.)
4. **Le format de sortie** — décris la forme du résultat attendu.

## 4. Teste en boucle
Relance le runtime (`make up` en local, ou redéploie selon la consigne) et
discute avec ton agent dans l'UI. Ajuste la description si le skill se déclenche
mal (trop / pas assez).

## 5. Mesure (optionnel mais ça impressionne le jury)
Crée un petit jeu de cas `eval/mon-skill.jsonl` (regarde l'exemple) puis :
```bash
python -m eval.run_eval eval/mon-skill.jsonl
```

## Checklist démo
- [ ] Le problème métier est dit en une phrase (qui, quelle douleur).
- [ ] Démo **live** sur le lab (pas de slides de capture d'écran).
- [ ] Le bon skill se déclenche au bon moment.
- [ ] Un garde-fou HITL est visible au moins une fois.
- [ ] Tu finis par : « voici qui s'en servirait dès lundi, et comment on mesure ».

## Anti-sèche : un bon skill vs un mauvais
- ✅ « Trie les factures fournisseurs… Use when facture/avoir/BC. Do NOT use pour RH. »
- ❌ « Aide avec les documents. » (trop vague → ne se déclenche jamais au bon moment)
