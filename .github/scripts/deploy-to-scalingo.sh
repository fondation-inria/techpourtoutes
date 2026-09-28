#!/usr/bin/env bash
# Deploys the archive of $SHA to $SCALINGO_APP and waits for that deployment to reach a terminal
# status, then writes the Matrix message reporting it on stdout and the status on $GITHUB_OUTPUT.
# A failed deploy is a normal outcome here, not an error: reporting it is the whole point.
set -euo pipefail

poll_interval=10
max_polls=120
timeout_minutes=$((poll_interval * max_polls / 60))

bearer=$(curl -sS -u ":$SCALINGO_API_TOKEN" -X POST https://auth.scalingo.com/v1/tokens/exchange |
  jq -r '.token // empty')
if [[ -z "$bearer" ]]; then
  echo "Échange du token Scalingo refusé : SCALINGO_API_TOKEN est-il défini dans les secrets du repo ?" >&2
  exit 1
fi

deployments_api() {
  local path="$1"
  shift
  curl -sS -H "Authorization: Bearer $bearer" -H "Content-Type: application/json" \
    "$SCALINGO_API_URL/v1/apps/$SCALINGO_APP/deployments$path" "$@"
}

# The archive of this exact SHA rather than the branch: what ships is what was tested,
# even when another push lands in the meantime.
response=$(deployments_api "" -X POST -d "$(jq -n --arg sha "$SHA" --arg repo "$GITHUB_REPOSITORY" \
  '{deployment: {git_ref: $sha, source_url: "https://github.com/\($repo)/archive/\($sha).tar.gz"}}')")
deployment_id=$(jq -r '.deployment.id // empty' <<<"$response")
if [[ -z "$deployment_id" ]]; then
  echo "Scalingo a refusé le déploiement sur l'app « $SCALINGO_APP » : $response" >&2
  exit 1
fi

status=""
duration=""
for _ in $(seq 1 "$max_polls"); do
  deployment=$(deployments_api "/$deployment_id")
  status=$(jq -r '.deployment.status // empty' <<<"$deployment")
  duration=$(jq -r '.deployment.duration // empty' <<<"$deployment")
  case "$status" in
    success | *-error | aborted) break ;;
  esac
  sleep "$poll_interval"
done

echo "status=${status:-pending}" >>"$GITHUB_OUTPUT"

case "$status" in
  success) icon="✅" ; label="Déploiement réussi" ;;
  build-error) icon="❌" ; label="Échec du déploiement : erreur au build" ;;
  hook-error) icon="❌" ; label="Échec du déploiement : le postdeploy a échoué" ;;
  crashed-error) icon="❌" ; label="Échec du déploiement : l'application n'a pas démarré" ;;
  timeout-error) icon="❌" ; label="Échec du déploiement : démarrage trop long" ;;
  aborted) icon="⚠️" ; label="Déploiement annulé" ;;
  *) icon="⏱️" ; label="Déploiement toujours en cours après ${timeout_minutes} minutes" ;;
esac

if [[ -n "$duration" && "$duration" -ge 60 ]]; then
  elapsed=" ($((duration / 60)) min $((duration % 60)) s)"
elif [[ -n "$duration" ]]; then
  elapsed=" (${duration} s)"
else
  elapsed=""
fi

jq -n \
  --arg headline "${icon} ${SCALINGO_APP} — ${label}${elapsed}" \
  --arg logs "$SCALINGO_DEPLOYMENTS_URL" \
  '{
    msgtype: "m.notice",
    body: "\($headline)\n\($logs)",
    format: "org.matrix.custom.html",
    formatted_body: "<b>\($headline)</b> · <a href=\"\($logs)\">journaux du déploiement</a>"
  }'
