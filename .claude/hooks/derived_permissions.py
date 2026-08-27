#!/usr/bin/env python3
"""
Hook PreToolUse pour Claude Code.
Dérive ses règles automatiquement de .claude/settings.json et
.claude/settings.local.json au lieu de dupliquer une allowlist séparée.
Claude est buggé sur la lecture des permissions avec des commandes bash chainées par des |
Ce hook permet de régler ce problème.
"""

import json
import os
import re
import sys

PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

# Commandes considérées "read-only" par défaut par Claude Code
# (cf. doc officielle : ls, cat, echo, pwd, head, tail, grep, find, wc,
# which, diff, stat, du, cd, et formes en lecture seule de git)
DEFAULT_READONLY = {
    "ls",
    "cat",
    "echo",
    "pwd",
    "head",
    "tail",
    "grep",
    "find",
    "wc",
    "which",
    "diff",
    "stat",
    "du",
    "cd",
}


def load_settings_files():
    """Charge et fusionne les règles allow/deny des fichiers de settings,
    settings.local.json ayant priorité sur settings.json."""
    paths = [
        os.path.join(PROJECT_DIR, ".claude", "settings.json"),
        os.path.join(PROJECT_DIR, ".claude", "settings.local.json"),
    ]
    allow, deny = [], []
    for p in paths:
        if not os.path.exists(p):
            continue
        try:
            with open(p) as f:
                data = json.load(f)
        except json.JSONDecodeError, OSError:
            continue
        perms = data.get("permissions", {})
        allow.extend(perms.get("allow", []))
        deny.extend(perms.get("deny", []))
    return allow, deny


def extract_bash_patterns(rules):
    """Ne garde que les règles de la forme Bash(...) et renvoie le contenu."""
    patterns = []
    for rule in rules:
        m = re.match(r"^Bash\((.*)\)$", rule)
        if m:
            patterns.append(m.group(1))
    return patterns


def pattern_to_regex(pattern):
    """
    Convertit un pattern façon Claude Code en regex :
    - 'prefix:*' -> matche 'prefix' ou 'prefix <suite>' (frontière de mot)
    - '*' générique -> n'importe quelle séquence
    - le wildcard final est optionnel s'il est le seul '*' du pattern
    """
    # Cas "prefix:*" (ancienne syntaxe)
    if pattern.endswith(":*") and pattern.count("*") == 1:
        prefix = re.escape(pattern[:-2])
        return rf"^{prefix}(\s.*)?$"

    # Cas générique avec '*' (peut apparaître n'importe où)
    parts = pattern.split("*")
    escaped = [re.escape(p) for p in parts]
    if len(parts) == 1:
        # pas de wildcard : correspondance exacte
        return rf"^{escaped[0]}$"

    regex = ".*".join(escaped)

    # Si le pattern se termine par un '*' unique, il devient optionnel
    if pattern.endswith("*") and pattern.count("*") == 1:
        base = re.escape(pattern[:-1].rstrip())
        return rf"^{base}(\s.*)?$"

    return rf"^{regex}$"


def split_pipeline(command):
    """
    Découpe une commande composée sur |, &&, ||, ; en ignorant les
    séparateurs situés à l'intérieur de guillemets (simples ou doubles).
    Best effort : ne gère pas les sous-shells imbriqués complexes.
    """
    # Nombre de guillemets non échappés impair -> commande ambiguë,
    # on ne prend pas de risque et on laisse le comportement par défaut.
    if (command.count('"') - command.count('\\"')) % 2 != 0:
        return None
    if (command.count("'") - command.count("\\'")) % 2 != 0:
        return None

    segments = []
    current = ""
    in_single = in_double = False
    i = 0
    n = len(command)
    while i < n:
        c = command[i]
        if c == "'" and not in_double:
            in_single = not in_single
            current += c
        elif c == '"' and not in_single:
            in_double = not in_double
            current += c
        elif not in_single and not in_double:
            # Séparateurs reconnus uniquement hors guillemets et
            # entourés d'espaces (ou en fin/début de commande) pour
            # coller au style des commandes générées par Claude
            two = command[i : i + 2]
            if two in ("||", "&&"):
                segments.append(current)
                current = ""
                i += 2
                continue
            if c in ("|", ";"):
                # on exige un espace avant (ou début de chaîne) pour '|'
                if c == "|" and i > 0 and command[i - 1] != " ":
                    current += c
                else:
                    segments.append(current)
                    current = ""
                    i += 1
                    continue
            else:
                current += c
        else:
            current += c
        i += 1
    segments.append(current)
    return [s.strip() for s in segments if s.strip()]


def segment_allowed(segment, bash_patterns):
    first_word = segment.split()[0] if segment.split() else ""
    if first_word in DEFAULT_READONLY:
        return True
    for pattern in bash_patterns:
        regex = pattern_to_regex(pattern)
        if re.match(regex, segment):
            return True
    return False


def main():
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(0)  # on laisse Claude Code gérer normalement

    if payload.get("tool_name") != "Bash":
        sys.exit(0)

    command = payload.get("tool_input", {}).get("command", "")
    if not command:
        sys.exit(0)

    allow_rules, deny_rules = load_settings_files()
    bash_allow_patterns = extract_bash_patterns(allow_rules)
    bash_deny_patterns = extract_bash_patterns(deny_rules)

    segments = split_pipeline(command)
    if segments is None:
        sys.exit(0)  # commande ambiguë -> comportement par défaut

    # Deny prioritaire : si un segment matche une règle deny, on bloque
    for seg in segments:
        for pattern in bash_deny_patterns:
            if re.match(pattern_to_regex(pattern), seg):
                print(
                    json.dumps(
                        {
                            "hookSpecificOutput": {
                                "hookEventName": "PreToolUse",
                                "permissionDecision": "deny",
                                "permissionDecisionReason": f"Segment '{seg}' "
                                "matches deny rule 'Bash({pattern})'",
                            }
                        }
                    )
                )
                sys.exit(0)

    # Allow seulement si TOUS les segments sont couverts
    if all(segment_allowed(seg, bash_allow_patterns) for seg in segments):
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "allow",
                        "permissionDecisionReason": "Tous les segments du pipeline "
                        "correspondent aux règles allow de settings.json",
                    }
                }
            )
        )
        sys.exit(0)

    # Sinon, on ne dit rien -> comportement par défaut (prompt normal)
    sys.exit(0)


if __name__ == "__main__":
    main()
