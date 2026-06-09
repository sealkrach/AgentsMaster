# Agentathon Lab — kit clef en main

Un environnement **prêt à l'emploi** pour faire concevoir des agents par le plus
grand nombre, en une journée, dans un cadre **gouverné** adapté à un contexte
régulé (banque/assurance).

Le principe : on ne construit pas une plateforme, on **livre des skills**. Le
runtime est un *commodity* (DeepAgents sur LangGraph) ; ce que les participants
produisent, ce sont des **skills** au format ouvert [agentskills.io](https://agentskills.io) —
réutilisables ensuite tels quels dans la vraie plateforme.

## Ce que ça fait
- Un **runtime DeepAgents/LangGraph** exposé en FastAPI (`/invoke`, `/stream`, `/health`).
- **Quatre sources de données mockées à comportement réel**, embarquées (zéro service
  à gérer) : relationnel **SQLite** (vrai SQL), vectoriel **TF-IDF/cosinus** (hors-ligne),
  graphe **networkx** (vraies traversées), corpus documentaire.
- **Quatre vrais serveurs MCP** devant ces sources → l'agent voit la topologie
  « tools = MCP » **identique à la prod** ; seuls les moteurs derrière sont mockés.
- **Trois topologies d'agent** prêtes à forker : `single`, `supervisor` (subagents),
  `swarm` (handoff). Sélection par `LAB_TOPOLOGY`.
- Les **skills chargés depuis ce repo** (`FilesystemBackend`) → revue PR + CI = gouvernance.
- **Progressive disclosure** : au démarrage l'agent ne voit que `name`+`description` ;
  le `SKILL.md` complet n'est lu que quand la tâche matche.
- **Human-in-the-loop** (`interrupt_on`) : validation avant toute écriture.
- **Données 100 % synthétiques** → zéro gate de conformité pour participer.
- Deux skills exemples : `invoice-triage` (contrôle de facture) et `entity-dossier`
  (**GraphRAG** : graphe + vecteur + relationnel).
- Un **scaffold de skill**, un **harnais d'eval**, une **UI de chat**.
- Le **provisioning OpenShift** de namespaces éphémères isolés (TTL + auto-teardown),
  runtime + 4 serveurs MCP.

➜ Détails du paysage de données, de la couche MCP et des topologies :
  [`docs/TOPOLOGIES.md`](docs/TOPOLOGIES.md).

## Démarrage rapide (local, pour tester)
Le plus simple — un seul process, sans serveurs MCP à lancer :
```bash
cp .env.example .env          # renseignez LAB_MODEL + la clé provider
make install
make up-inproc                 # http://localhost:8080  (MCP_MODE=inproc)
```
Dans l'UI, tapez : `contrôle la facture INV-2026-0044` ou `fais-moi le dossier du fournisseur Acme`.

Pour reproduire fidèlement la topologie MCP (deux terminaux) :
```bash
make mcp                       # terminal 1 : les 4 serveurs MCP
make up                        # terminal 2 : le runtime (MCP_MODE=mcp)
```

Changer de topologie : `LAB_TOPOLOGY=supervisor make up-inproc` (ou `swarm`).

Lancer l'eval du skill exemple :
```bash
make eval
```

Créer un skill :
```bash
make new-skill name=mon-skill
```

## Lab de l'événement (OpenShift, namespaces éphémères)
Une équipe = un namespace isolé, plafonné, deny-by-default, auto-détruit à TTL.
```bash
TTL_HOURS=48 ./scripts/provision_namespace.sh equipe-alpha
```
Détails (image, secret modèle, reaper) : [`deploy/openshift/README.md`](deploy/openshift/README.md).

## Carte du repo
```
runtime/        # FastAPI + assemblage DeepAgents + topologies (le commodity)
mock_sources/   # 4 moteurs mock embarqués : SQLite, cosinus, networkx, corpus
mcp_servers/    # 4 vrais serveurs MCP (FastMCP) devant les sources
skills/         # AGENTS.md + _TEMPLATE + invoice-triage + entity-dossier (GraphRAG)
data/synthetic/ # landscape.json : docs, chunks, entités, relations, jobs — jamais de prod
ui/             # UI de chat (montre skills + outils en direct)
eval/           # jeu de cas + runner async (la gate "ça marche")
scripts/        # new_skill.sh, provision_namespace.sh
deploy/openshift/  # namespace éphémère + runtime + mcp-servers + reaper
docs/           # FACILITATOR.md + PARTICIPANT.md + TOPOLOGIES.md
```

## Pour les organisateurs / participants
- Organiser l'événement : [`docs/FACILITATOR.md`](docs/FACILITATOR.md)
- Construire un skill : [`docs/PARTICIPANT.md`](docs/PARTICIPANT.md)

## Notes d'honnêteté
- **Squelette, pas produit fini.** À adapter à votre socle. Faites-le passer par
  votre revue sécurité avant tout usage réel.
- **DeepAgents évolue vite** : l'API ici suit la doc officielle au moment du build —
  épinglez les versions (`pip freeze`) avant l'événement et vérifiez la signature
  de `create_deep_agent`.
- **Exécution de scripts dans les skills** : pour exécuter du code embarqué, DeepAgents
  requiert un *sandbox backend*. Le chemin doré de ce kit n'en dépend pas (skills =
  instructions + outils). Sur OpenShift, sandboxez l'exécution (gVisor/Kata) si vous
  l'activez.
- **Égress** : restreignez la NetworkPolicy au seul endpoint modèle approuvé.
- **Modèle** : pointez `LAB_MODEL` vers votre endpoint approuvé (Bedrock/Azure),
  idéalement en auth par rôle plutôt qu'une clé en clair.
