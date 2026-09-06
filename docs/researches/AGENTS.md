# How research works in `docs/researches/`

This directory is the shared research memory for tarakdingdung. Any agent, in
any session, uses it the same way: **scrape raw material into `references/`,
then distill it into `summaries/`.** Read this file end to end before adding,
editing, or citing anything here.

---

## 1. Layout

```
docs/researches/
├── AGENTS.md                     ← this file (the rules)
├── references/
│   ├── 00_Contents_Overview.md   ← index of every reference file
│   ├── 01_<Title>.md
│   ├── 02_<Title>.md
│   └── ...
└── summaries/
    ├── 00_Contents_Overview.md   ← index of every summary file
    ├── 01_<Title>.md
    ├── 02_<Title>.md
    └── ...
```

- **`references/`** — raw, near-verbatim captures of individual web sources. One
  source (or one tightly-scoped cluster from the same source) per file. This is
  the evidence layer: minimally processed, maximally faithful to the original.
- **`summaries/`** — synthesised, easy-to-digest write-ups that combine **two or
  more** references into a single coherent answer to a question. This is the
  decision layer: what we actually read when we build.

Every non-trivial fact in a summary must trace back to at least one file in
`references/`. If it can't be traced, it doesn't belong in a summary.

---

## 2. File naming

**`XX_The_Title.md`**

- `XX` — a two-digit, zero-padded decimal counter: `01`, `02`, … `09`, `10`, …
  `99`. It is unique and monotonically increasing **within its folder**
  (`references/` and `summaries/` each have their own independent sequence).
- `00` is reserved for `00_Contents_Overview.md` in both folders. Real content
  starts at `01`.
- `The_Title` — a short, human-readable title in `Title_Case_With_Underscores`.
  No spaces, no punctuation other than underscores. Keep it under ~60
  characters. Make it specific enough to recognise in a list
  (`04_Kelly_Criterion_Position_Sizing.md`, not `04_Notes.md`).
- **Numbers are permanent.** Once `07_...` exists and is referenced, that number
  is burned. If you delete a file, leave its number retired — do **not**
  renumber later files, because summaries cite references by number and
  renumbering silently breaks that backtracking. A retired number gets a
  tombstone line in the folder's `00_Contents_Overview.md` (see §5).
- To find the next number: take the highest `XX` currently listed in that
  folder's `00_Contents_Overview.md` (including tombstones) and add one.

---

## 3. `references/` — raw scraping dump

**Purpose:** capture what a source actually said, so we never have to re-fetch
it and so summaries can be audited against it.

**When you add a reference:**

1. Pick the next free number for `references/`.
2. Create `references/XX_The_Title.md` with this shape:

   ```markdown
   # <Title>

   - **Source URL:** <full canonical URL>
   - **Author / Publisher:** <name, or "unknown">
   - **Published:** <date the source was published, or "unknown">
   - **Retrieved:** <YYYY-MM-DD you fetched it>
   - **Retrieved by:** <agent / session note>
   - **Type:** <article | paper | docs | forum thread | video transcript | book excerpt | ...>
   - **Topic tags:** <comma-separated, e.g. momentum, risk-management, backtesting>

   ---

   ## Raw content

   <The scraped text, pasted in as faithfully as practical. Preserve headings,
   lists, formulae, tables, and code. Trim site chrome (nav, ads, cookie
   banners, unrelated "related posts"). Do not paraphrase. Do not editorialise.
   Long is fine — this layer is allowed to be big.>

   ---

   ## Capture notes

   <Optional. Anything about the capture itself: paywalled and only the abstract
   was reachable, JS-rendered and partially extracted, PDF converted to text,
   figures dropped, etc. This is about fidelity of the capture, not analysis.>
   ```

3. Add a one-line entry to `references/00_Contents_Overview.md` (see §5).

**Rules for `references/`:**

- **Dump it all.** When in doubt, capture more. Multiple sources on the same
  question each get their own file — do not merge them here.
- **Near-verbatim only.** No synthesis, no opinion, no "this means we should…".
  That is what `summaries/` is for.
- **Treat as append-mostly.** After a reference is committed, don't rewrite its
  `Raw content`. Fix typos in metadata, add to `Capture notes`, but if the
  source materially changed, capture a **new** reference and tombstone or
  cross-link the old one.
- One source, one file. If a single page covers several distinct topics you care
  about, it's still one file (the page is the unit); split only when it's
  genuinely separate URLs.

---

## 4. `summaries/` — digested synthesis

**Purpose:** answer a question we care about, in a form we can act on, built by
combining and reconciling multiple references.

**When you add a summary:**

1. Pick the next free number for `summaries/`.
2. Create `summaries/XX_The_Title.md` with this shape:

   ```markdown
   # <Title>

   - **Question:** <the specific question this summary answers>
   - **Last updated:** <YYYY-MM-DD>
   - **Status:** <draft | reviewed | superseded by NN>
   - **Topic tags:** <comma-separated>

   ---

   ## TL;DR

   <3–8 sentences or bullets. The answer, up front. Someone should be able to
   read only this and make a reasonable call.>

   ## Detail

   <The full synthesis. Reconcile agreements and contradictions across the
   references. Call out consensus vs. minority view vs. disputed. Include the
   concrete numbers, formulae, parameter ranges, and caveats an implementer
   needs. Cite as you go: "(ref 03)", "(refs 03, 07)".>

   ## Open questions / gaps

   <What the current references do NOT settle. What to research next.>

   ---

   ## References used

   Every source this summary draws on, by number and title, for backtracking:

   - `references/03_<Title>.md`
   - `references/07_<Title>.md`
   - `references/11_<Title>.md`
   ```

3. Add a one-line entry to `summaries/00_Contents_Overview.md` (see §5).

**Rules for `summaries/`:**

- **At least two references.** A summary is a synthesis. If only one source
  exists, either find more or leave it as a reference until you can.
- **The "References used" list is mandatory** and must list every reference the
  content relies on. Inline `(ref NN)` markers must all appear in that list.
- Keep claims tied to references. If you add analysis that isn't in any
  reference (your own reasoning, a calculation), mark it explicitly as
  derived/authored so a later reader knows it isn't sourced.
- When new references change the picture, **update the summary in place** and
  bump `Last updated`. If the conclusion flips, set the old summary's `Status`
  to `superseded by NN` and write a new one rather than silently rewriting
  history that other docs may cite.

---

## 5. `00_Contents_Overview.md` (both folders)

An always-current index of that folder. One line per file, in number order, each
with a short description of what's inside so a reader can pick the right file
without opening all of them.

**Format:**

```markdown
# References — Contents Overview
<!-- or: # Summaries — Contents Overview -->

Index of every file in this folder. Keep in sync on every add, update, or
retire. Numbers are never reused.

| #  | File | Description |
|----|------|-------------|
| 01 | `01_Momentum_Factor_Primer.md` | Investopedia-level overview of cross-sectional momentum, lookback windows, known failure modes. |
| 02 | `02_Kelly_Criterion_Position_Sizing.md` | Derivation of full/fractional Kelly, why practitioners use half-Kelly. |
| 03 | ~~`03_...`~~ | **Retired** 2026-09-06 — duplicate of 02, merged in. |
```

- Update this file **in the same change** that adds, updates, or retires a
  content file. An index that lies is worse than no index.
- Retired entries stay in the table with strikethrough and a reason, so the
  number is visibly burned.

---

## 6. End-to-end workflow

1. **Frame the question.** Write down the specific thing you need to know (e.g.
   "what is the most robust, well-evidenced entry algorithm for a v1 automated
   trading system?").
2. **Scrape.** Search the web, open the credible sources, and capture each one
   into `references/` per §3. Aim for a spread: foundational explainers, primary
   research / papers, practitioner write-ups, and dissenting views. Update
   `references/00_Contents_Overview.md`.
3. **Synthesise.** Once you have ≥2 relevant references, write or update a file
   in `summaries/` per §4 that answers the framed question, citing every
   reference used. Update `summaries/00_Contents_Overview.md`.
4. **Loop.** If the summary has open questions, go back to step 2 for those.

---

## 7. Quality bar for sources

Prefer, in rough order: peer-reviewed papers and working papers (SSRN, arXiv
q-fin) → books by recognised practitioners → reputable financial/tech
publications and established quant blogs → exchange and broker documentation →
forum threads and videos (use for leads and sentiment, corroborate before
relying on).

For every source, capture enough metadata (§3) that a reader can judge its
authority and recency themselves. Flag marketing content, unbacked claims, and
anything that promises returns without discussing risk or drawdown.

---

## 8. Checklist before you finish a research pass

- [ ] Every new source is a file in `references/` with full metadata.
- [ ] `references/00_Contents_Overview.md` lists every reference file, in order.
- [ ] Each conclusion lives in a `summaries/` file, not only in `references/`.
- [ ] Every summary has a filled-in **References used** list.
- [ ] Every inline `(ref NN)` marker resolves to an entry in that list.
- [ ] `summaries/00_Contents_Overview.md` lists every summary file, in order.
- [ ] No number was reused; any deletion left a tombstone.
