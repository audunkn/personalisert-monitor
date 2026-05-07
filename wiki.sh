#!/usr/bin/env bash
# Push dokumentasjon fra github_wiki/ til GitHub Wiki
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
WIKI_TMP=$(mktemp -d)

cd "$WIKI_TMP"
git init -q
git remote add origin https://github.com/audunkn/personalisert-monitor.wiki.git
git pull origin master -q 2>/dev/null || true
cp "$REPO_DIR/github_wiki/"*.md .
git add -A

if git diff --cached --quiet; then
    echo "Ingen endringer i wiki."
else
    git commit -q -m "oppdater wiki $(date +%Y-%m-%d)"
    git push -u origin master
    echo "Wiki oppdatert."
fi

rm -rf "$WIKI_TMP"
