#!/usr/bin/env bash
# Push dokumentasjon fra github_wiki/ til GitHub Wiki
# Mappestruktur i wikien speiler repoets src/intelligence_monitor/-struktur.
# github_wiki/ i koden er alltid flat — mappetilhørighet styres av denne filen.
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
WIKI_TMP=$(mktemp -d)

cd "$WIKI_TMP"
git init -q
git remote add origin https://github.com/audunkn/personalisert-monitor.wiki.git
git pull origin master -q 2>/dev/null || true

# Returnerer wiki-undermappe for en gitt fil, eller tom streng for root.
_wiki_mappe() {
    case "$1" in
        vault_skriver_py_dokumentasjon.md|\
        kjører_py_dokumentasjon.md|\
        obsidian_vakt_py_dokumentasjon.md|\
        rss_py_dokumentasjon.md)
            echo "innhenter" ;;
        *)
            echo "" ;;
    esac
}

for fil in "$REPO_DIR/github_wiki/"*.md; do
    filnavn="$(basename "$fil")"
    mappe="$(_wiki_mappe "$filnavn")"
    if [ -n "$mappe" ]; then
        mkdir -p "$mappe"
        cp "$fil" "$mappe/$filnavn"
    else
        cp "$fil" "$filnavn"
    fi
done

git add -A

if git diff --cached --quiet; then
    echo "Ingen endringer i wiki."
else
    git commit -q -m "oppdater wiki $(date +%Y-%m-%d)"
    git push -u origin master
    echo "Wiki oppdatert."
fi

rm -rf "$WIKI_TMP"
