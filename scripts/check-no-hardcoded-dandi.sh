#!/bin/bash
# Pre-commit hook to prevent hardcoded DANDI identifiers in frontend code.
# Instance-specific values (instance name, RRID) should come from the
# backend /api/info/ endpoint via the instance store, not be hardcoded.
#
# Patterns checked:
#   - "DANDI:" used as an identifier prefix in string literals
#   - "DANDI Archive" used as a publisher/archive name in string literals
#   - "SCR_017571" hardcoded RRID
#
# Files excluded:
#   - This script itself
#   - Test files
#   - HomeView.vue (static marketing text)
#   - constants.ts (static URLs like dandiarchive.org are not instance-specific)

set -euo pipefail

ERRORS=0

for file in "$@"; do
    # Skip excluded files
    case "$file" in
        */check-no-hardcoded-dandi.sh) continue ;;
        *__tests__*|*.test.*|*.spec.*) continue ;;
        */HomeView/*) continue ;;
        */constants.ts) continue ;;
        */directives/index.ts) continue ;;  # fallback title before store loads
    esac

    # Check for DANDI: as identifier prefix in string/template literals
    # Match patterns like `DANDI:${...}`, "DANDI:", 'DANDI:'
    if grep -nE '("|'\''|`)\s*DANDI:' "$file" >/dev/null 2>&1; then
        echo "$file: found hardcoded 'DANDI:' identifier prefix — use instanceName from the instance store"
        ERRORS=$((ERRORS + 1))
    fi

    # Check for lowercase dandi: used as citation key prefix (followed by digits or ${)
    # Excludes schema URIs like dandi:OpenAccess, dandi:EmbargoedAccess
    if grep -nE '("|'\''|`)\s*dandi:\$\{' "$file" >/dev/null 2>&1 || \
       grep -nE '("|'\''|`)\s*dandi:[0-9]' "$file" >/dev/null 2>&1; then
        echo "$file: found hardcoded 'dandi:' identifier prefix — use instanceName.toLowerCase() from the instance store"
        ERRORS=$((ERRORS + 1))
    fi

    # Check for "DANDI Archive" as publisher name in string literals
    # Exclude HTML comments (<!-- ... -->)
    if grep -nE "(\"|\`|').*DANDI Archive" "$file" | grep -vE '^\s*<!--' >/dev/null 2>&1; then
        echo "$file: found hardcoded 'DANDI Archive' — use instanceName from the instance store"
        ERRORS=$((ERRORS + 1))
    fi

    # Check for hardcoded RRID
    if grep -nE 'SCR_017571' "$file" >/dev/null 2>&1; then
        echo "$file: found hardcoded RRID 'SCR_017571' — use instanceIdentifier from the instance store"
        ERRORS=$((ERRORS + 1))
    fi
done

if [ "$ERRORS" -gt 0 ]; then
    echo ""
    echo "Found $ERRORS file(s) with hardcoded DANDI identifiers."
    echo "Use the instance store (web/src/stores/instance.ts) for dynamic values."
    exit 1
fi
