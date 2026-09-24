#!/usr/bin/env bash
# Builds the Matrix message announcing what a push on main just sent to production.
# Reads BEFORE / AFTER / GITHUB_REPOSITORY from the environment, writes the payload on stdout.
set -euo pipefail

owner="${GITHUB_REPOSITORY%/*}"
repo="${GITHUB_REPOSITORY#*/}"

# A branch creation or a force-push leaves no usable commit to diff against: report the tip alone.
if [[ "$BEFORE" =~ ^0+$ ]] || ! git cat-file -e "${BEFORE}^{commit}" 2>/dev/null; then
  range="${AFTER}~1..${AFTER}"
else
  range="${BEFORE}..${AFTER}"
fi

pull_request_numbers() {
  git log --format=%H "$range" | while read -r sha; do
    gh api "repos/${GITHUB_REPOSITORY}/commits/${sha}/pulls" --jq '.[].number'
  done | sort -un
}

pull_request() {
  gh api graphql -F owner="$owner" -F repo="$repo" -F number="$1" \
    --jq '.data.repository.pullRequest' -f query='
      query($owner: String!, $repo: String!, $number: Int!) {
        repository(owner: $owner, name: $repo) {
          pullRequest(number: $number) {
            number
            title
            url
            closingIssuesReferences(first: 10) { nodes { number title url } }
          }
        }
      }'
}

items=$(for number in $(pull_request_numbers); do pull_request "$number"; done | jq -s '.')

# A commit pushed straight to main belongs to no pull request: fall back to its subject.
if [[ "$(jq 'length' <<<"$items")" -eq 0 ]]; then
  items=$(git log --format=%s "$range" |
    jq -R '{number: null, title: ., url: null, closingIssuesReferences: {nodes: []}}' |
    jq -s '.')
fi

jq -n --argjson items "$items" --arg title "🚀 Mise en production — ${repo}" '
  def escape: gsub("&"; "&amp;") | gsub("<"; "&lt;") | gsub(">"; "&gt;");

  def entry: if .number then "\(.title) (#\(.number))" else .title end;
  def entry_html:
    if .url
    then "\(.title | escape) (<a href=\"\(.url)\">#\(.number)</a>)"
    else (.title | escape) end;

  def issues: .closingIssuesReferences.nodes;
  def issues_text:
    if (issues | length) > 0
    then " — clôt " + (issues | map("#\(.number) \(.title)") | join(", "))
    else "" end;
  def issues_html:
    if (issues | length) > 0
    then " — clôt " + (issues | map("<a href=\"\(.url)\">#\(.number)</a> \(.title | escape)") | join(", "))
    else "" end;

  {
    msgtype: "m.notice",
    body: ([$title] + ($items | map("• " + entry + issues_text)) | join("\n")),
    format: "org.matrix.custom.html",
    formatted_body: ("<b>\($title | escape)</b><ul>"
      + ($items | map("<li>" + entry_html + issues_html + "</li>") | join(""))
      + "</ul>")
  }
'
