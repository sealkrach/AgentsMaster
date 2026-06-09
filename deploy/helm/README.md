# Déploiement K8s-agnostique — Helm + Gateway API

Alternative portable au déploiement OpenShift (`deploy/openshift/`). Tourne sur
EKS, GKE, AKS, k3s, kubeadm — et sur OpenShift, qui sait lire un Ingress/HTTPRoute.

**Modèle :** une **release Helm = un use case = un namespace éphémère**. Le namespace
est la frontière d'isolation (runtime + 4 serveurs MCP + une topologie) ; le use case
lui-même est un **skill** (`SKILL.md`). Le teardown est natif (`helm uninstall` +
suppression du namespace), avec le reaper TTL en backstop.

> Le namespace s'aligne sur ce que vous voulez isoler et jeter indépendamment. Ici on
> l'aligne sur le **use case / sponsor**. On peut tout aussi bien l'aligner sur l'**équipe**
> (remplacez simplement `usecase` par votre identifiant d'équipe) — c'est un choix de
> nommage, pas d'architecture.

---

## Prérequis cluster (NON fournis par le chart)

Ces éléments dépendent de votre cluster et doivent exister **avant** :

1. **Gateway API** — les CRDs installés (`kubectl get crd httproutes.gateway.networking.k8s.io`)
   et un **contrôleur** : Envoy Gateway, Istio, Contour, ou NGINX Gateway Fabric.
2. **Une Gateway partagée** dont un listener **autorise les routes des namespaces
   éphémères** (voir l'exemple plus bas). C'est elle qui rend les hostnames joignables.
3. **Un CNI qui APPLIQUE les NetworkPolicies** (Calico, Cilium). Sans lui, le
   `default-deny` du chart est un *no-op silencieux* — l'isolation n'est qu'apparente.
4. **Un endpoint modèle approuvé** (Bedrock/Azure/Anthropic) joignable depuis le cluster,
   et le `modelEgressCIDR` restreint à cet endpoint.

> Si vous n'avez pas (encore) de Gateway, vous pouvez tout valider en
> `kubectl port-forward` (voir teardown/smoke) — zéro dépendance réseau.

---

## 1. L'image

```bash
docker build -t registry.internal/innovation/agentathon-lab:latest .
docker push registry.internal/innovation/agentathon-lab:latest
```

## 2. La Gateway partagée (une fois, côté infra)

Exemple minimal. **Le point clé est `allowedRoutes`** : il laisse les HTTPRoutes
des namespaces `agentathon/ephemeral=true` s'attacher à la Gateway.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: agentathon-gateway
  namespace: gateway-infra
spec:
  gatewayClassName: <votre-gatewayclass>     # ex: envoy-gateway, istio, contour
  listeners:
    - name: http
      protocol: HTTP
      port: 80
      hostname: "*.lab.example.internal"
      allowedRoutes:
        namespaces:
          from: Selector
          selector:
            matchLabels:
              agentathon/ephemeral: "true"
```

Pour du TLS, ajoutez un listener HTTPS (cert-manager + Issuer, ou certificat géré
par le contrôleur). Hors OpenShift, le TLS n'est pas automatique.

## 3. Le Secret modèle (par namespace de use case)

```bash
kubectl create ns agentathon-tri-factures 2>/dev/null || true
kubectl -n agentathon-tri-factures create secret generic lab-model \
  --from-literal=model='anthropic:claude-sonnet-4-5' \
  --from-literal=api_key='<clé, ou vide si auth par rôle>'
```

> En banque : préférez l'auth par rôle (IRSA/Bedrock, Workload Identity/Azure) à une
> clé en clair. Dans ce cas, mettez `model.apiKey.enabled=false` et adaptez les `env`.

## 4. Déployer un use case

```bash
helm install tri-factures deploy/helm/agentathon-lab \
  -n agentathon-tri-factures --create-namespace \
  --set usecase=tri-factures \
  --set topology=single \
  --set image.repository=registry.internal/innovation/agentathon-lab \
  --set image.tag=latest \
  --set gateway.baseDomain=lab.example.internal \
  --set networkPolicy.modelEgressCIDR=10.0.0.0/8
```

Runtime joignable sur `http://tri-factures.lab.example.internal/`.
Changez `--set topology=supervisor` (ou `swarm`) pour les autres orchestrations.
Un autre use case = une autre release : `helm install dossier-fournisseur … --set usecase=dossier-fournisseur`.

## 5. Démanteler

- **Explicite :** `helm uninstall tri-factures -n agentathon-tri-factures && kubectl delete ns agentathon-tri-factures`
- **Automatique (TTL) :** le reaper supprime tout namespace expiré.

## Le reaper (auto-teardown TTL, une fois)

```bash
kubectl apply -f deploy/helm/reaper/reaper.yaml
```

Crée un namespace `agentathon-admin`, un ServiceAccount + ClusterRole (`get/list/delete`
sur les namespaces) et un CronJob (toutes les 15 min) qui supprime les namespaces
`agentathon/ephemeral=true` dont `creationTimestamp + agentathon/ttl-hours` est dépassé.
Adaptez le namespace d'admin et l'image `kubectl` (ici `bitnami/kubectl`) à votre contexte.

---

## Validation AVANT l'événement (votre pré-flight)

`helm` rend, mais ne prouve pas que ça tourne. Faites, dans l'ordre :

```bash
# 1) Le chart est syntaxiquement valide et rend correctement
helm lint deploy/helm/agentathon-lab
helm template tri-factures deploy/helm/agentathon-lab \
  -n agentathon-tri-factures --set usecase=tri-factures | kubectl apply --dry-run=server -f -

# 2) Déployer UN use case de test, atteindre le runtime
helm install tri-factures deploy/helm/agentathon-lab -n agentathon-tri-factures --create-namespace --set usecase=tri-factures
kubectl -n agentathon-tri-factures port-forward svc/lab-runtime 8080:8080
curl -s localhost:8080/health

# 3) UN vrai /invoke avec le modèle approuvé — l'étape qui prouve ou casse tout
curl -s localhost:8080/invoke -H 'content-type: application/json' \
  -d '{"message":"Liste les jobs en statut error et le fournisseur concerné."}'

# 4) Recommencer avec --set topology=supervisor puis swarm
```

Tant que l'étape 3 n'est pas passée sur **chaque topologie**, c'est « prêt à tester »,
pas « prêt pour les équipes ».

---

## Basculer sur les VRAIES bases (`dataPlane=real`)

Par défaut le chart déploie les serveurs MCP **mock** (moteurs embarqués). Pour les
brancher sur les vraies bases via le catalogue `idp_mcp` (voir `prod-mcp/`), changez
**uniquement** le plan de données — le runtime et les contrats d'outils ne bougent pas.

```bash
# 1) Le Secret de connexions (DSN Postgres EN LECTURE SEULE, creds Arango/Qdrant, embedding)
kubectl -n agentathon-tri-factures create secret generic idp-backends \
  --from-literal=IDP_PG_DSN='postgresql://idp_ro@pg:5432/idp' \
  --from-literal=IDP_ARANGO_URL='http://arango:8529' \
  --from-literal=IDP_ARANGO_DB='idp' \
  --from-literal=IDP_ARANGO_USER='idp_ro' \
  --from-literal=IDP_ARANGO_PASSWORD='...' \
  --from-literal=IDP_QDRANT_URL='http://qdrant:6333' \
  --from-literal=IDP_QDRANT_COLLECTION='documents' \
  --from-literal=IDP_EMBEDDING_PROVIDER='http' \
  --from-literal=IDP_EMBEDDING_ENDPOINT='https://<endpoint-embedding-approuvé>/embeddings' \
  --from-literal=IDP_EMBEDDING_MODEL='<même-modèle-que-l-index-Qdrant>'

# 2) Installer en mode réel, en pointant l'IMAGE IDP (qui embarque idp_mcp + ses deps)
helm upgrade --install tri-factures deploy/helm/agentathon-lab \
  -n agentathon-tri-factures --create-namespace \
  --set usecase=tri-factures \
  --set dataPlane=real \
  --set mcp.image=registry.internal/idp/idp-platform:latest \
  --set mcp.backendSecret=idp-backends \
  --set networkPolicy.backendsEgress[0].cidr=10.0.0.0/8 \
  --set 'networkPolicy.backendsEgress[0].ports={5432,8529,6333}'
```

Ce que `dataPlane=real` change automatiquement : la **commande** des pods MCP
(`python -m idp_mcp <name>`), l'**image** MCP (`mcp.image`), l'injection du **Secret**
de connexions (`envFrom`), et une **NetworkPolicy d'egress** vers vos bases. Pré-requis
identiques à `prod-mcp/` : rôle Postgres en lecture seule, et `IDP_EMBEDDING_MODEL`
EXACTEMENT le modèle ayant indexé Qdrant.
