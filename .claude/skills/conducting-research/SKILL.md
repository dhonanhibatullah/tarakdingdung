---
name: conducting-research
description: Use when asked to research a topic, technology, algorithm, library, or approach for the tarakdingdung project; when adding findings to docs/researches/; when scraping web sources for later reference; when writing or updating a literature summary; or when citing or backtracking existing research.
---

# Conducting Research

## Overview

`docs/researches/` is tarakdingdung's shared, cross-session research memory.
It has two tiers: **`references/`** holds raw, near-verbatim captures of
individual web sources (the evidence layer); **`summaries/`** holds synthesised
write-ups that combine two or more references into an actionable answer (the
decision layer). Never skip the reference tier and write a lone summary — every
claim in a summary must trace back to a filed reference.

**The authoritative rules live in `docs/researches/AGENTS.md`. Read it before
adding, editing, or citing anything.** This skill is the map; that file is the
territory.

## When to Use

- "Research the best X for our project" / "look into how Y works"
- Adding scraped web content, papers, or docs to the repo for later use
- Writing a summary that synthesises multiple sources
- Someone asks where a conclusion came from → backtrack via a summary's
  **References used** list
- **Not for:** transient one-off lookups you won't reuse, or project code
  conventions (those go in `AGENTS.md` files).

## Workflow

1. **Frame the question** — write the specific thing you need to know.
2. **Scrape** — find credible sources (papers > practitioner books > reputable
   press / quant blogs > docs > forums). Capture each into
   `references/XX_Title.md` using the template in `AGENTS.md` §3: metadata
   block (URL, author, published, retrieved date, type, tags) + near-verbatim
   `Raw content`. One source per file. Dump generously; do not paraphrase.
3. **Index references** — add a row to `references/00_Contents_Overview.md`.
4. **Synthesise** — once ≥2 relevant references exist, write or update
   `summaries/XX_Title.md` per `AGENTS.md` §4: Question / TL;DR / Detail with
   inline `(ref NN)` markers / Open questions / **References used** list.
5. **Index summaries** — add a row to `summaries/00_Contents_Overview.md`.
6. **Loop** — chase the summary's open questions back through step 2.

## Quick Reference

| | `references/` | `summaries/` |
|---|---|---|
| Content | raw scraped source, verbatim | synthesised digest |
| Per file | one source | one question, ≥2 sources |
| Editing | append-mostly; capture a new file if the source changed | update in place, bump `Last updated` |
| Mandatory | metadata block | **References used** list + inline `(ref NN)` |

## Key Rules

- **Naming:** `XX_Title_In_Title_Case.md`, two-digit zero-padded, independent
  sequence per folder, `00` reserved for the overview.
- **Numbers are permanent.** Never renumber — summaries cite references by
  number. A deleted file leaves a retired number with a tombstone row in the
  folder's `00_Contents_Overview.md`.
- **Update the matching `00_Contents_Overview.md` in the same change** that adds
  or retires a file. An index that lies is worse than none.
- **Every `(ref NN)` marker must resolve** to an entry in that summary's
  References used list.

## Common Mistakes

- Writing a summary straight from web results without filing the raw sources →
  the conclusion can't be audited later. File references first.
- One reference file covering several sources → one source per file.
- Renumbering after a deletion → breaks every summary that cited the old
  number. Tombstone instead.
- Forgetting the References used list, or letting it drift from the inline
  markers.
- Editing a reference's `Raw content` after the fact → capture a new reference.
