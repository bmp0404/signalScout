# frontend-core

Entry point, top-level app shell, API client, and the three page-level views (Discover, Backtest, Digest) that make up the Signal Scout single-page app. This module owns routing (tab state), data fetching orchestration, and global styling.

## frontend/src/main.jsx
Bootstraps the React app by mounting `<App />` into the `#root` DOM node inside `React.StrictMode`, and imports the global stylesheet.

- No exported components or functions — this is the Vite/React entry script.

## frontend/src/App.jsx
Renders the page header/nav and switches between the three tabs, firing a page-view analytics beacon on every tab change.

- `App()` — renders the sticky header (title, tagline, tab nav for Discover/Backtest/Digest) and the active tab's page component; on each tab change calls `api.pageView({ path, referrer })` (best-effort, errors are swallowed so analytics never break the UI).

## frontend/src/api/client.js
Thin fetch wrapper plus the single `api` object listing every backend endpoint the frontend calls; JSON error bodies are surfaced via `err.detail`/`err.status`.

- `request(path, options) -> Promise<any>` — wraps `fetch`, throws an `Error` (with `.status` and message from the response's `detail` field when present) on non-OK responses, otherwise resolves the parsed JSON body.
- `api.overview() -> Promise` — `GET /api/overview`.
- `api.candidates(cohort = 'discovery') -> Promise` — `GET /api/candidates?cohort=<cohort>`.
- `api.candidate(id) -> Promise` — `GET /api/candidates/:id`.
- `api.backtest() -> Promise` — `GET /api/backtest`.
- `api.concentrations() -> Promise` — `GET /api/concentrations`.
- `api.latestDigest() -> Promise` — `GET /api/digests/latest`.
- `api.generateDigest() -> Promise` — `POST /api/digests/generate`.
- `api.sendDigest() -> Promise` — `POST /api/digests/send`.
- `api.subscribe(payload) -> Promise` — `POST /api/subscribers` with a JSON body.
- `api.sendTestDigest(payload) -> Promise` — `POST /api/digest/test` with a JSON body.
- `api.pageView(payload) -> Promise` — `POST /api/analytics/page-view` with a JSON body.
- `api.runDiscovery() -> Promise` — `POST /api/discovery/run`.
- `api.discoveryStatus() -> Promise` — `GET /api/discovery/status`.

## frontend/src/pages/Backtest.jsx
Loads and renders the historical backtest report: headline recall/lead-time stats, a score-distribution chart, top predictive signal types, and a sortable per-founder results table that opens the evidence panel.

- `Metric({ label, value, detail })` — renders a single labeled stat tile (used for recall, lead time, false positives, pre-connected counts).
- `Backtest()` — fetches `api.backtest()` on mount, shows loading/error/empty states, then renders headline copy, four `Metric` tiles, a `ScoreDistribution` chart, a bar list of `top_signal_types`, and a results table where clicking a row opens `EvidencePanel` for that `person_id`.

## frontend/src/pages/Digest.jsx
Public/operator dual-mode view of the generated founder digest: public visitors see a signup prompt only, while `operatorMode` unlocks generate/send controls and the full entry list.

- `Digest({ operatorMode = false })` — in public mode renders `DigestSignup` plus a static "digest is server-managed" notice; in operator mode loads the latest digest via `api.latestDigest()`, provides GENERATE (`api.generateDigest()`) and SEND PREVIEW (`api.sendDigest()`) buttons, and renders each digest entry (name, score, thesis, top signals, orbit/intro context, why-now, and `ContactLinks`).

## frontend/src/pages/Discover.jsx
The main discovery browser: fetches ranked candidates for a cohort (discovery vs. founder/ground-truth), optionally exposes operator controls to trigger and poll a live discovery pipeline run, and toggles between a single-card browsing view and a full table view.

- `Discover({ showOperatorControls = false })` — loads candidates via `api.candidates(cohort)` and the source mix via `api.overview()`; when operator controls are shown, `runDiscovery()` calls `api.runDiscovery()` then polls `api.discoveryStatus()` every 1200ms (`POLL_MS`) until the job reaches `done`/`error`, refreshing the candidate list and highlighting newly discovered IDs on completion; renders `DigestSignup`, cohort/view toggle buttons, `PipelineProgress`, `SourceMix`, and either `CandidateTable` or `CandidateCard` (with prev/next paging) plus `EvidencePanel` on selection.

## frontend/src/index.css
Global stylesheet: imports Tailwind's base/components/utilities layers, sets the page body font/colors, and defines the shared `.label-mono` utility class used for small uppercase mono labels across components.
