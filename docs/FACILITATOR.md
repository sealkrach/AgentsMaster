# Guide facilitateur — Agentathon

> Principe directeur : on ne construit pas une plateforme, on **livre des skills**
> qui atterrissent chez de vrais utilisateurs. Chaque skill a un sponsor métier
> et un chemin d'adoption. C'est ce qui distingue cet agentathon d'un théâtre
> d'innovation.

## Format
- **Durée** : 1,5 jour — kickoff l'après-midi J0, journée pleine de build J1, démos en fin de J1.
- **Lieu** : présentiel ou hybride.
- **Public** : ouvert au plus grand nombre — métiers ET ingénieurs.
- **Pré-travail (1 semaine avant)** : un primer « agent literacy » d'1h + le walkthrough du lab.
  Objectif : le jour J est 100 % build, pas de setup.

## Tracks
1. **Track métier** — le skill = un `SKILL.md` seul, branché sur les outils déjà câblés. Aucun code. Ouvert à tous.
2. **Track builder** — les ingénieurs ajoutent de nouveaux outils (MCP) ou des helpers.

**Composition d'équipe** : un binôme **métier + ingénieur**. Le métier possède la
`description` et le playbook (c'est l'artefact qui décide du déclenchement) ;
l'ingénieur possède l'outil/le script.

## Énoncés de problème (à collecter auprès des sponsors AVANT)
Chaque business unit fournit un problème réel avec un sponsor identifié. Modèle :

```
## Problème — <titre>
**Sponsor** : <nom, BU>
**Douleur actuelle** : <ce qui coince aujourd'hui, chiffré si possible>
**Utilisateur cible** : <qui utilisera le skill au quotidien>
**À quoi ressemble un succès** : <résultat concret et mesurable>
**Données / outils nécessaires** : <ce qu'il faudra, version synthétique pour le lab>
**Critère d'adoption** : <comment on saura que c'est utilisé après l'événement>
```

## Déroulé (run-of-show)
| Quand | Quoi |
|---|---|
| J−7 | Inscriptions ouvertes, primer + walkthrough lab envoyés |
| J0 14h | Kickoff, énoncés de problème dévoilés, constitution des binômes |
| J0 15h | Provisioning des namespaces (`make ns-up team=…`), prise en main |
| J1 9h–16h | Build (mentors/coachs flottants Paris/Mumbai, canal d'aide ouvert) |
| J1 16h | Gel du code, démos **sur le lab réel** (pas de slides) |
| J1 17h | Délibération, annonce, storytelling publié |

## Jury & barème
Panel : **sponsor métier + tech lead + délégué CISO** (rôles, pas noms).

| Critère | Poids | Question |
|---|---|---|
| Adoption | 35 % | De vrais utilisateurs s'en serviraient-ils dès lundi ? |
| Ça tourne | 25 % | Démo live sur le runtime gouverné, pas une maquette |
| Qualité de la description | 20 % | Le skill se déclenche-t-il au bon moment, pas trop, pas trop peu ? |
| Conformité / garde-fous | 10 % | HITL au bon endroit, pas de donnée prod, outils déclarés |
| Clarté de la démo | 10 % | Le problème et la valeur sont-ils limpides ? |

**Prix** : la **visibilité** (pitch au comité, mise en avant newsletter) et le
**fast-track en production** — bien plus motivant que du swag.

## Le pont qui tue le « joujoue »
Annoncez **dès le kickoff** : les skills gagnants (et les meilleurs suivants)
ont un fast-track engagé vers la vraie plateforme. Comme le format est identique
(`SKILL.md` dans le repo gouverné), il y a **zéro re-travail** entre l'agentathon
et la prod. Sans ce pont, c'est du théâtre.

## Après l'événement
- Le sponsor + l'équipe data branchent le skill sur les vrais outils MCP (à la
  place des mocks) et le poussent dans le repo gouverné.
- L'observabilité (LangSmith/Phoenix) fournit la métrique d'adoption qui clôt la
  gate de delivery : *rien n'est « done » tant que ce n'est pas utilisé.*
- Storytelling post-event → recrute la cohorte suivante.
