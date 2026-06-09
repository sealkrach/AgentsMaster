# Déploiement OpenShift — namespaces éphémères

Chaque équipe obtient un namespace **isolé** (`agentathon-<equipe>`) avec quota,
limites, NetworkPolicy deny-by-default, et le runtime du lab. Les namespaces
sont **auto-détruits** à expiration par un CronJob "reaper".

## 1. Construire et pousser l'image
```bash
docker build -t registry.internal/innovation/agentathon-lab:latest .
docker push registry.internal/innovation/agentathon-lab:latest
```

## 2. Le secret modèle (par namespace, ou via un opérateur de réplication)
```bash
oc -n agentathon-equipe-alpha create secret generic lab-model \
  --from-literal=model='anthropic:claude-sonnet-4-5' \
  --from-literal=api_key='<clé ou laissez vide si Bedrock/IAM>'
```
> En banque : préférez l'auth par rôle (IRSA/Bedrock, Workload Identity/Azure)
> plutôt qu'une clé en clair. Adaptez les `env` du Deployment en conséquence.

## 3. Provisionner une équipe
```bash
TTL_HOURS=48 IMAGE=registry.internal/innovation/agentathon-lab:latest \
  ./scripts/provision_namespace.sh equipe-alpha
```

## 4. Démanteler
- Manuel : `oc delete ns agentathon-equipe-alpha`
- Automatique : le **reaper** ci-dessous supprime tout namespace expiré.

## Le reaper (auto-teardown par TTL)
À déployer une fois dans un namespace d'admin. Il lit le label
`agentathon/expires-at` et supprime les namespaces dépassés.

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: agentathon-reaper
spec:
  schedule: "*/15 * * * *"        # toutes les 15 min
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: agentathon-reaper   # RBAC: delete sur namespaces
          restartPolicy: Never
          containers:
            - name: reaper
              image: registry.internal/tools/oc-cli:latest
              command: ["/bin/sh","-c"]
              args:
                - |
                  now=$(date -u +%s)
                  for ns in $(oc get ns -l agentathon/ephemeral=true -o name); do
                    exp=$(oc get $ns -o jsonpath='{.metadata.annotations.agentathon/expires-at}')
                    [ -z "$exp" ] && continue
                    if [ "$(date -u -d "$exp" +%s)" -lt "$now" ]; then
                      echo "Suppression $ns (expiré $exp)"; oc delete $ns
                    fi
                  done
```

## Garde-fous appliqués
- **Isolation** : un namespace par équipe, deny-by-default réseau.
- **Plafond ressources** : ResourceQuota + LimitRange.
- **Pas de données prod** : seules les données synthétiques du repo sont montées.
- **Skills gouvernés** : l'image embarque le `skills/` du repo (revu en PR) —
  rien n'est téléchargé depuis un marketplace externe.
- **Égress restreint** : à pointer vers le seul endpoint modèle approuvé.
