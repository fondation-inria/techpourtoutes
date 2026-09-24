#!/usr/bin/env bash
# Waits for the Scalingo deployment of $SHA to reach a terminal status, then writes the Matrix
# message reporting it on stdout and the status on $GITHUB_OUTPUT. A failed deploy is a normal
# outcome here, not an error: reporting it is the whole point of the script.
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

# Deployments come back newest first, so the first match is the run this push triggered.
# Comparing seven characters covers both the short and the full form of git_ref.
deployment() {
  local response
  response=$(curl -sS -H "Authorization: Bearer $bearer" \
    "$SCALINGO_API_URL/v1/apps/$SCALINGO_APP/deployments")
  if ! jq -e 'has("deployments")' <<<"$response" >/dev/null; then
    echo "Scalingo n'a renvoyé aucun déploiement pour l'app « $SCALINGO_APP » : $response" >&2
    exit 1
  fi
  jq -c --arg sha "$SHA" '[.deployments[] | select(.git_ref[0:7] == $sha[0:7])][0] // empty' \
    <<<"$response"
}

status=""
duration=""
for _ in $(seq 1 "$max_polls"); do
  found=$(deployment)
  if [[ -n "$found" ]]; then
    status=$(jq -r '.status' <<<"$found")
    duration=$(jq -r '.duration // empty' <<<"$found")
  fi
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
