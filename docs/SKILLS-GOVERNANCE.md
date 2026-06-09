# Gouvernance des skills — « livrer un agent = merger une PR »

Le **use case est un skill** ; le **runtime et les outils MCP sont le socle gouverné**.
On ne reviewe pas du framework, on reviewe un `SKILL.md`. Git EST la gouvernance.

## Le flux
```
Auteur métier            CI (skills-ci.yml)              Reviewer            Prod
─────────────            ──────────────────              ────────            ────
copie skills/_TEMPLATE   validate_skills (frontmatter)   description scope   merge =
écrit SKILL.md      ─▶   parité des contrats        ─▶   outils approuvés ─▶ skill vivant
(desc + instructions)    garde SQL                       eval présente       (FilesystemBackend
ajoute eval/<dir>.jsonl  [eval si activée]                                    sur le repo gouverné)
```

1. **Créer** : `./scripts/new_skill.sh <nom>` (part de `skills/_TEMPLATE`). Pas de Python,
   pas de PR sur le cœur de plateforme.
2. **PR** : la CI valide automatiquement (voir checklist). Si `RUN_SKILL_EVAL=true`, elle
   exécute aussi l'eval avec le modèle approuvé (mode in-proc, aucune base requise).
3. **Review** : un humain vérifie 3 choses (voir checklist) — c'est léger et lisible métier.
4. **Merge = live** : le runtime lit `skills/` via le `FilesystemBackend` ; au déploiement
   suivant le skill est disponible (progressive disclosure : chargé seulement si sa
   `description` matche la demande).

## Ce que la CI vérifie (bloquant)
- `name` et `description` présents ; `description` assez détaillée (elle décide du déclenchement).
- Le `SKILL.md` a un corps.
- **Parité des contrats** : `prod-mcp/idp_mcp` expose exactement les mêmes outils que le kit.
- **Garde SQL** : seules les requêtes lecture seule passent.
- (Optionnel) **Eval** du skill avec le modèle approuvé.

## Checklist de review (humain)
- [ ] La `description` cadre-t-elle bien QUAND l'agent doit se déclencher (ni trop large, ni trop étroit) ?
- [ ] Le skill n'utilise que des **outils du catalogue approuvé** (lecture seule ; écritures via HITL) ?
- [ ] Une **eval** existe (`eval/<dir>.jsonl`) — « train as you build » ?

## Étiquettes de gouvernance (par skill, en tête de PR)
`Owner` (Paris/Mumbai) · `Bucket` (MCP/Agentic) · `Risk` 🟢🟡🔴 · `Data sensitivity`
(public/internal/confidential/restricted) · `HITL` (oui/non) · `Reviews` (CISO/CTO si besoin).

## Désactiver un skill qui se comporte mal
Revert la PR. Le skill disparaît du repo gouverné → il n'est plus chargé. Pas de hotfix infra.
