# Verifikasjon — A0b: Obsidian Web Clipper

*Dato: 2026-04-23*

---

## Resultat: GODKJENT

Alle must-have-krav er oppfylt. Røyktesten er bestått med 3 ekte artikler.

---

## Tester

```
6/6 passed (uv run pytest tester/ -v)

tester/test_db_init.py::test_idempotens         PASSED
tester/test_db_init.py::test_yaml_synk          PASSED
tester/test_vault_skriver.py::test_filnavn_og_frontmatter   PASSED
tester/test_vault_skriver.py::test_element_id_konsistens    PASSED
tester/test_vault_skriver.py::test_ugyldig_bilde_url        PASSED
tester/test_vault_skriver.py::test_rollback                 PASSED
```

---

## Røyktest

3 artikler klippet via Obsidian Web Clipper og verifisert i SQLite:

| id | tittel | url |
|----|--------|-----|
| 1 | Predictions for the Future of RAG | https://jxnl.co/writing/2024/06/05/predictions-for-the-future-of-rag/ |
| 2 | Integrating AI Evals Into Your AI App | https://www.decodingai.com/p/integrating-ai-evals-into-your-ai-app |
| 3 | Using LLM-as-a-Judge For Evaluation: A Complete Guide | https://hamel.dev/blog/posts/llm-judge/ |

Alle filer flyttet til `vault/behandlet/` etter prosessering.

---

## Avvik fra plan — godkjent

**Plan linje 33** spesifiserte `tittel` og `kilde_id` som YAML-frontmatter-felt.

**Implementasjonen:** `tittel` skrives som `# H1`-heading (standard Obsidian-konvensjon, bedre leseopplevelse). `kilde_id` lagres kun i SQLite (er en intern nøkkel uten verdi i markdown).

**Beslutning:** Avviket godkjent. `plan.md` oppdatert til å reflektere faktisk implementasjon.

---

## Funn under røyktest (fikset)

| Funn | Fix |
|------|-----|
| `VAULT_ROT` pekte på `OBSIDIAN/` i stedet for `OBSIDIAN/monitor-evals/` | Oppdatert i `.env` |
| Web Clipper skriver `source`-felt, ikke `url` | `obsidian_vakt.py` aksepterer begge |

---

## Manuelt uverifisert

- **Dedup** — klipp samme URL to ganger (lav risiko, logikk er enhetstestet)
- **Bildenedlasting** — klipp side med bilder (lav risiko, enhetstestet med mock)
