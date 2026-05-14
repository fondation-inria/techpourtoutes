#!/bin/bash

# Merges staging into main, triggering a production deploy on Scalingo.
set -e

# Prints text with colour based on the message's importance level
print_text() {
  case "$2" in
    info)    COLOR="96m" ;;
    success) COLOR="92m" ;;
    warning) COLOR="93m" ;;
    danger)  COLOR="91m" ;;
    *)       COLOR="0m"  ;;
  esac
  printf "\e[${COLOR}%b\e[0m" "$1"
}

# Exits the script after printing a warning message
exit_with_message() {
  print_text "$1\n" "warning"
  exit 1
}

print_text "\nTech Pour Toutes: merge sur main, déploiement en production\n" "info"
print_text "--------------------------------------------\n\n"

# Gets the current branch by looking for `*` character
# - `s/` is for substitution
# - `/p` prints the result
current_branch=$(git branch | sed -n -e 's/^\* \(.*\)/\1/p')

print_text "Vérification de la branche : "
if [ "$current_branch" != "staging" ]; then
  print_text "Échec\n" "danger"
  exit_with_message "Vous devez être sur la branche 'staging' pour déployer. Abandon."
fi
print_text "OK\n" "success"

print_text "Vérification du statut git : "
if [[ "$(git status --porcelain 2>/dev/null)" != "" ]]; then
  print_text "Échec\n" "danger"
  exit_with_message "'git status' doit être propre pour déployer. Abandon."
fi
print_text "OK\n" "success"

print_text "Synchronisation avec origin/staging : "
git fetch origin staging
local_sha=$(git rev-parse staging)
remote_sha=$(git rev-parse origin/staging)
if [ "$local_sha" != "$remote_sha" ]; then
  print_text "Échec\n" "danger"
  exit_with_message "La branche locale 'staging' n'est pas synchronisée avec origin. Faites 'git pull' d'abord. Abandon."
fi
print_text "OK\n" "success"

print_text "\n"

git checkout main
git pull origin main
print_text "Récupération de 'main' : OK\n" "success"

print_text "\nVoici ce qui va être déployé en production :\n"
print_text "--------------------------------------------\n"
git log main..staging --oneline
print_text "--------------------------------------------\n\n"

read -p "Souhaitez-vous toujours déployer ? (y/n) : " deploy_choice

if [ "$deploy_choice" == "y" ]; then
  if ! git merge --ff-only staging 2>/dev/null; then
    git checkout staging
    exit_with_message "'main' contient des commits absents de 'staging'. Un fast-forward est impossible. Résolvez cela manuellement. Abandon."
  fi
  git push origin main
  git checkout staging
  print_text "\nstaging merged into main. Scalingo s'occupe du déploiement.\n" "success"
else
  git checkout staging
  print_text "\nDéploiement annulé - no merge of staging into main.\n" "warning"
  exit 1
fi
