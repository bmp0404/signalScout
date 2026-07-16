# frontend-components

Reusable presentational components and view-model helpers shared across the Discover, Backtest, and Digest pages: candidate cards/tables, evidence detail panels, signal badges/timelines, pipeline progress, and the digest signup form.

## frontend/src/components/CandidateCard.jsx
Single-candidate "profile card" view used in Discover's card-browsing mode, showing a score ring, thesis, top signals, and contact links.

- `initials(name) -> string` — returns up to two uppercase initials from a full name (used inside the avatar circle).
- `CandidateCard({ candidate, rank, onViewEvidence })` — renders a ranked candidate's avatar/initials with an SVG score-arc, name, school/location lines, numeric score, thesis, `SignalBadge` list, orbit/warm-intro context, `ContactLinks`, and a "VIEW EVIDENCE" button that calls `onViewEvidence`.

## frontend/src/components/CandidateTable.jsx
Filterable, sortable list/table of candidates used in Discover's "Browse all" mode, with view tabs (provider/cross-source/all), area and source filters, and an unknowns-only toggle.

- `CandidateTable({ candidates, onSelect, highlightIds, defaultView = 'provider', defaultUnknownsOnly = true })` — derives filter option lists (areas, sources) from `candidates`, applies view filter (via `filterCandidatesByView`), area/source/unknowns filters, and score/name sorting, then renders each row as a card showing name, score, signal count, thesis, source-count badges, `SignalBadge` list, and orbit context; clicking a row calls `onSelect(candidate)`; rows in `highlightIds` get a "NEW" badge and highlighted border.

## frontend/src/components/candidateViews.js
Pure data-shaping helpers defining the candidate "view" tabs (provider discoveries / cross-source / all) and the filtering logic behind them, consumed by `CandidateTable` and unit-tested in `candidateViews.test.js`.

- `CANDIDATE_VIEWS` — array of `[value, label]` pairs: `['provider', 'Provider discoveries']`, `['cross-source', 'Cross-source']`, `['all', 'All candidates']`.
- `filterCandidatesByView(candidates, view) -> Array` — returns candidates where `discovery_origin === 'provider_search'` for `'provider'`, candidates with `source_diversity >= 2` for `'cross-source'`, or the full unfiltered list for any other view (`'all'`).

## frontend/src/components/candidateViews.test.js
Node `test`/`assert` unit tests verifying `filterCandidatesByView` correctly isolates provider-discovered candidates, cross-source candidates (diversity >= 2), and passes through the full cohort for the "all" view.

- No exports — this is a test file, not a module consumed elsewhere.

## frontend/src/components/ContactLinks.jsx
Renders a row of outbound contact links (GitHub, LinkedIn, X, Email, Site) for a candidate or digest entry.

- `ContactLinks({ links, className = '' })` — maps a `links` object (key -> URL) to labeled `target="_blank"` anchor tags using a fixed label map; renders nothing if `links` is empty/absent.

## frontend/src/components/DigestSignup.jsx
Self-contained email signup form (with optional signal-interest/seed-account personalization fields) shown at the top of the Discover and Digest pages.

- `DigestSignup()` — manages form state for email/frequency/signalInterests/seedAccounts, validates that email is present, submits via `api.subscribe(payload)`, and shows a confirmation panel with a "USE ANOTHER EMAIL" reset button on success, or an inline error message on failure.

## frontend/src/components/EvidencePanel.jsx
Modal overlay showing the full evidence "receipt" for one candidate: score breakdown table, signal timeline, and network connections, fetched by person ID.

- `EvidencePanel({ personId, onClose })` — fetches `api.candidate(personId)` on mount/`personId` change, shows loading/error states (with retry), and on success renders the candidate's name/school/region, `ContactLinks`, source-count badges, a score-breakdown table (`profile.breakdown.items` with evidence label, date, source, strength×weight, points, plus a raw/recency/diversity/age formula summary), a `SignalTimeline`, and a list of network `connections`; clicking the backdrop or CLOSE calls `onClose`.

## frontend/src/components/PipelineProgress.jsx
Live status widget for the discovery pipeline run (scrape -> resolve -> enrich -> score), polled from Discover while a run is in progress.

- `countLabel(name, count) -> string` — formats the per-stage count label (e.g. "N profiles", "N unknowns", "N enriched", "scored") based on stage name.
- `Dot({ status })` — renders a small status-colored circle (done/active/error/pending) for one pipeline stage.
- `PipelineProgress({ status })` — renders nothing if `status` is absent or idle; otherwise renders a horizontal stage tracker with `Dot` indicators, stage labels/hints, connecting lines, a RUNNING/DONE/ERROR badge, and an error message when `status.error` is set.

## frontend/src/components/ScoreDistribution.jsx
Overlaid histogram comparing founder vs. control score distributions for the Backtest page, with a threshold marker.

- `histogram(scores) -> number[]` — buckets an array of 0-100 scores into 10 fixed-width bins and returns per-bin counts.
- `ScoreDistribution({ founderScores, controlScores, threshold })` — renders a bar-chart histogram (founders in olive, controls in gray, overlaid per bin) with a vertical line marking `threshold` and a legend.

## frontend/src/components/SignalBadge.jsx
Small pill component showing one evidence signal's category icon, summary text, and source label; also exports the shared source-name lookup used by other components.

- `SOURCE_LABELS` — map of raw source keys (github, pdl, coresignal, semantic_scholar, devpost, graph) to human-readable display names.
- `sourceLabel(source) -> string|null` — looks up a human-readable label for a raw source key, falling back to the raw key itself (or `null` if no source given).
- `SignalBadge({ signal })` — renders a bordered pill with a category icon (competition/code/research/hackathon/connection/fellowship/debate/etc.), the signal's `summary` or `type` text, and its source label.

## frontend/src/components/SignalTimeline.jsx
Horizontal dated timeline of a candidate's evidence signals with a breakout-date marker, used inside `EvidencePanel`.

- `SignalTimeline({ timeline, breakout })` — positions each `timeline` entry along a horizontal axis proportional to its date, color-coded by category, with a hover tooltip (date, summary/type, source) and a vertical "breakout" marker line at the `breakout` date if provided; renders "No signals." if `timeline` is empty.

## frontend/src/components/SourceMix.jsx
Stacked-bar summary of how many signals came from each data source, shown at the top of the Discover page.

- `SourceMix({ mix })` — renders nothing if `mix` is empty; otherwise renders a proportional stacked horizontal bar (one segment per source, colored via a fixed per-source palette) plus a legend with each source's label and percentage share, sorted by count descending.
