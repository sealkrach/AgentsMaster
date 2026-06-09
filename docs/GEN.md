# Génération intelligente d'éléments agentiques

Le kit expose deux générateurs LLM qui produisent du code production-ready
à partir d'une description en langage naturel.

---

## Prérequis

Définissez `ANTHROPIC_API_KEY` dans votre `.env` (copié depuis `.env.example`).
Le modèle utilisé est `claude-sonnet-4-6` (environ 5–15 secondes par génération).

```bash
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
```

---

## Générer un skill

Un skill est un fichier `SKILL.md` qui indique à l'agent *quand* et *comment*
traiter un cas métier. L'agent le lit automatiquement au démarrage.

### Via l'interface graphique

1. Ouvrez `http://localhost:8080` (runtime démarré avec `make up-inproc`)
2. Dans le panneau **Créer un élément** → onglet **Skill**
3. Saisissez un nom en kebab-case (`contrat-renouvellement`)
4. Décrivez le cas métier en français
5. Cliquez **Générer** — les étapes s'affichent en temps réel
6. Après succès, le skill apparaît automatiquement dans la liste

### Via la ligne de commande

```bash
make gen-skill name=contrat-renouvellement \
  description="Vérifie les contrats arrivant à échéance et déclenche leur renouvellement"

# Prévisualisation sans écriture
make gen-skill name=contrat-renouvellement \
  description="..." --dry-run   # ajouter dans le Makefile ou appeler directement :
python scripts/gen_skill.py --name contrat-renouvellement \
  --description "..." --dry-run
```

### Ce qui est créé

```
skills/
└── contrat-renouvellement/
    ├── SKILL.md        ← frontmatter YAML + instructions numérotées
    └── references/     ← répertoire pour documents de référence (vide)
```

### Tester

```bash
make up-inproc
# Dans l'UI : tapez "Quels contrats arrivent à échéance ?"
# L'agent doit activer le skill (visible dans le panneau)
```

---

## Générer un serveur MCP

Un serveur MCP expose une source de données fictive (mock) via le protocole
Model Context Protocol. Il produit 4 fichiers interconnectés.

### Via l'interface graphique

1. Dans le panneau **Créer un élément** → onglet **Serveur MCP**
2. Nom kebab-case du serveur (`audit-trail`)
3. Description de la source de données
4. Cliquez **Générer** — le port alloué s'affiche pendant la génération
5. Après succès, relancez le runtime pour charger les nouveaux outils

### Via la ligne de commande

```bash
make gen-mcp name=audit-trail \
  description="Logs d'audit métier : acteur, date, type d'action, ressource cible"

# Prévisualisation
python scripts/gen_mcp.py --name audit-trail \
  --description "..." --dry-run
```

### Ce qui est créé

| Fichier | Contenu |
|---|---|
| `mock_sources/_generated.py` | Classe `AuditTrailSource` avec données fictives |
| `mcp_servers/servers_generated.py` | Fonction factory `_audit_trail()` + dicts `GENERATED_PORTS/FACTORIES` |
| `runtime/tools_generated.py` | Outils LangChain in-process (mode `MCP_MODE=inproc`) |
| `runtime/config_generated.py` | Entrée `"audit-trail": http://127.0.0.1:9105/mcp` |

### Démarrer le serveur et tester

```bash
# Mode MCP (vrai serveur HTTP) :
python -m mcp_servers audit-trail   # démarre sur http://127.0.0.1:9105/mcp
make up                             # runtime avec MCP

# Mode inproc (tout-en-un, plus simple) :
make up-inproc
curl http://localhost:8080/info | python3 -m json.tool | grep audit
```

---

## Allocation automatique des ports

Les ports 9101–9104 sont réservés aux 4 sources initiales.
`gen_mcp.py` lit tous les ports `9xxx` existants et alloue `max + 1` :

| Serveur | Port |
|---|---|
| documents | 9101 |
| relational | 9102 |
| vector | 9103 |
| graph | 9104 |
| 1er généré | 9105 |
| 2ème généré | 9106 |
| … | … |

---

## Dry-run

Les deux générateurs acceptent `--dry-run` (CLI) ou la case **Aperçu seul** (UI).
En dry-run, aucun fichier n'est écrit — la sortie est affichée à l'écran.
Utile pour inspecter la réponse du LLM avant de committer.

---

## Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| `ANTHROPIC_API_KEY absent` | Variable non définie | Ajouter dans `.env` |
| `nom invalide` | Majuscules ou espaces | Utiliser `kebab-case` : `a-z`, `0-9`, `-` |
| `skill déjà existant` | Le dossier `skills/<name>/` existe | Choisir un autre nom ou supprimer manuellement |
| `serveur déjà existant` | Nom dans `servers_generated.py` | Choisir un autre nom |
| `< 3 blocs Python` | Le LLM n'a pas respecté le format | Relancer ou utiliser `--dry-run` pour inspecter |
| `Erreur API Anthropic` | Quota dépassé ou réseau | Vérifier la console Anthropic |
| Outils absents de `/info` | Runtime pas relancé | `make up-inproc` après génération |

---

## Endpoints API

Les générateurs sont aussi accessibles via HTTP depuis n'importe quel client :

```bash
# Générer un skill (SSE streaming)
curl -X POST http://localhost:8080/gen-skill \
  -H "Content-Type: application/json" \
  -d '{"name":"contrat-renouvellement","description":"...","dry_run":true}' \
  --no-buffer

# Générer un serveur MCP (SSE streaming)
curl -X POST http://localhost:8080/gen-mcp \
  -H "Content-Type: application/json" \
  -d '{"name":"audit-trail","description":"..."}' \
  --no-buffer
```

Format des événements SSE :

| `type` | Champs | Description |
|---|---|---|
| `gen:line` | `text` | Ligne de sortie du script (peut contenir `[STEP:x]` ou `[PORT:x]`) |
| `gen:done` | `code` | Génération terminée (code 0 = succès) |
| `gen:error` | `code` | Génération échouée (code non-nul) |
