#!/usr/bin/env bash
# Provisionne un namespace ÉPHÉMÈRE et isolé pour une équipe de l'agentathon,
# puis y déploie le runtime du lab.
#
#   ./scripts/provision_namespace.sh equipe-alpha
#
# Pré-requis : `oc login` effectué avec un compte habilité, et l'image du
# runtime poussée dans votre registre (voir IMAGE plus bas / Dockerfile).
#
# Le namespace porte un label de TTL ; un CronJob "reaper" (voir
# deploy/openshift/README.md) supprime les namespaces expirés => auto-teardown.
set -euo pipefail

TEAM="${1:-}"
TTL_HOURS="${TTL_HOURS:-48}"
IMAGE="${IMAGE:-registry.internal/innovation/agentathon-lab:latest}"
LAB_TOPOLOGY="${LAB_TOPOLOGY:-single}"

if [[ -z "$TEAM" ]]; then
  echo "Usage: ./scripts/provision_namespace.sh <nom-equipe>"; exit 1
fi

NS="agentathon-${TEAM}"
EXPIRES="$(date -u -d "+${TTL_HOURS} hours" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ)"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "▶ Namespace=$NS  TTL=${TTL_HOURS}h  image=$IMAGE"

export NS TEAM EXPIRES IMAGE LAB_TOPOLOGY
envsubst < "$ROOT/deploy/openshift/namespace.yaml"   | oc apply -f -
envsubst < "$ROOT/deploy/openshift/mcp-servers.yaml" | oc apply -f -
envsubst < "$ROOT/deploy/openshift/runtime.yaml"     | oc apply -f -

echo "✅ Provisionné. Route :"
oc -n "$NS" get route lab-runtime -o jsonpath='{.spec.host}{"\n"}' 2>/dev/null || \
  echo "   (la route apparaîtra dans quelques secondes : oc -n $NS get route)"
