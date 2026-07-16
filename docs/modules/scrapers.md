# Scrapers

The scrapers module collects raw evidence from external sources (GitHub, Devpost, Semantic Scholar) and curated fixture files, converting each into the shared `Signal` (and sometimes `GraphEdge`) domain records that the scoring module consumes. Every scraper is designed to fail soft — partial or total source failures degrade gracefully to an empty result rather than raising.

## backend/scrapers/__init__.py
Empty package marker file; no code.

## backend/scrapers/base.py
Defines the shared abstract scraper contract that concrete scrapers implement.

- `BaseScraper` — abstract base class establishing the common scraper interface: a `name` attribute identifying the source, and a `scrape()` method contract requiring implementations to never raise on partial failure and instead return whatever was successfully collected.
  - `BaseScraper.scrape() -> list[Signal]` — abstract method; concrete scrapers collect and return signals from their source, degrading gracefully (returning partial/empty results) rather than raising on failure.

## backend/scrapers/devpost_scraper.py
Scrapes public Devpost hackathon portfolio and project pages via stdlib regex (no official API) to emit hackathon win/finalist signals and teammate connection edges; source is public HTML at devpost.com, no auth/env vars required.

- `DevpostScraper` — per-person collector of Devpost hackathon history and teammate relationships, parsing defensively since markup can change.
  - `DevpostScraper.__init__(max_projects=3, request_gap_seconds=0.5)` — sets up a `requests.Session` with a browser-like User-Agent, caps how many projects are fetched per person, and sets the delay between project page requests.
  - `DevpostScraper._get(path) -> str | None` — fetches a Devpost page by path, returning the HTML text or `None` on any non-200 response or request exception (logged, never raised).
  - `DevpostScraper.user_projects(username) -> list[str]` — extracts the ordered, de-duplicated list of project slugs linked from a user's public portfolio page.
  - `DevpostScraper.github_username(username) -> str | None` — extracts a GitHub username explicitly linked from a user's public Devpost profile page, if present.
  - `DevpostScraper.project(slug) -> dict | None` — fetches and parses a project page into a dict with title, URL, team members (username/display name pairs), and per-hackathon submission info (hackathon name, won/finalist flags, prize text).
  - `DevpostScraper.collect(person, devpost_username) -> tuple[list[Signal], list[GraphEdge]]` — for a person's Devpost username, fetches up to `max_projects` projects they're confirmed team members of, emitting a `hackathon_win` signal (strength 0.8) for won submissions or `hackathon_finalist` (strength 0.6) for finalist submissions, plus `hackathon_teammate` graph edges to every other team member on each project.
  - `DevpostScraper._submission_date(hackathon, fallback) -> str` (static) — best-effort submission date derived from a 4-digit year found in the hackathon name, falling back to a provided date string.
  - `DevpostScraper._project_date(project, fallback) -> str` (static) — best-effort project date taken from the year in the first submission's hackathon name that matches, falling back to a provided date string.

## backend/scrapers/github_scraper.py
The only live (non-seeded) scraper: pulls a GitHub user's public profile, repos, and social/follow data via the GitHub REST API to derive builder, star-project, prolific, and student signals plus follow edges. Requires the `GITHUB_TOKEN` env var (used by the caller to construct `GithubClient`); without a token the pipeline falls back to the seeded fixture `data/seed_signals/github_seeded.json` so the demo doesn't break.

- `parse_grad_year(bio) -> int | None` — best-effort graduation-year extraction from a GitHub bio string, matching patterns like "class of 2027", "'27", or "2027 grad".
- `looks_like_student(bio) -> bool` — returns whether a bio matches student-related keywords (e.g. "undergrad", "high school", "class of") or a university-name hint (e.g. "MIT", "Stanford", ".edu").
- `GithubClient` — thin authenticated wrapper around the GitHub REST API; every method fails soft (returns `None`/`[]`) rather than raising.
  - `GithubClient.__init__(token)` — builds a `requests.Session` with a Bearer token authorization header and the GitHub API version header.
  - `GithubClient._get(path, params=None)` — issues a GET request against the GitHub API, returning parsed JSON, or `None` on rate-limit (403 with zero remaining), any non-200 status, or a request exception.
  - `GithubClient.user(username) -> dict | None` — fetches a user's public profile.
  - `GithubClient.repos(username) -> list[dict]` — fetches up to 100 of a user's public repos sorted by last-pushed.
  - `GithubClient.social_accounts(username) -> list[dict]` — fetches a user's linked social accounts.
  - `GithubClient.following(username, limit=100) -> list[dict]` — fetches accounts the user follows, capped at `limit`.
  - `GithubClient.followers(username, limit=100) -> list[dict]` — fetches the user's followers, capped at `limit`.
  - `GithubClient.repo_contributors(owner, repo, limit=30) -> list[dict]` — fetches a repo's contributors, capped at `limit`.
  - `GithubClient.repo_stargazers(owner, repo, limit=20) -> list[dict]` — fetches users who starred a repo (a one-way signal, not mutual), capped at `limit`.
  - `GithubClient.repo_forkers(owner, repo, limit=15) -> list[dict]` — fetches a repo's forks, capped at `limit`.
  - `GithubClient.repo_issues(owner, repo, limit=20) -> list[dict]` — fetches a repo's issues (GitHub's endpoint includes PRs), sorted by most recently updated, capped at `limit`.
  - `GithubClient.org_members(org, limit=30) -> list[dict]` — fetches an organization's members, capped at `limit`.
  - `GithubClient.user_orgs(username) -> list[dict]` — fetches the organizations a user belongs to.
- `GithubScraper` — orchestrates per-user signal collection from `GithubClient` data, implementing `BaseScraper`.
  - `GithubScraper.__init__(client, usernames, display_names=None)` — stores the `GithubClient`, the list of usernames to scrape, and an optional login-to-display-name override map.
  - `GithubScraper.scrape() -> list[Signal]` — iterates all configured usernames, collecting each user's signals via `scrape_user` and logging (never raising) on per-user failure.
  - `GithubScraper.scrape_user(username, user=None) -> list[Signal]` — fetches (or reuses) a user's profile and repos, then emits: a `github_early_builder` signal (strength 0.7) if the account has 3+ repos; a `github_star_project` signal per repo with 100+ stars (strength 0.9 if 1000+, else 0.6); a `github_prolific` signal (strength 0.5) if the user has 30+ repos; and a `student_builder` signal (strength 0.7) if the bio matches `looks_like_student`.
  - `GithubScraper.follow_edges(username, name) -> list[GraphEdge]` — builds `github_follows` graph edges from each of the user's followers to the user.

## backend/scrapers/seeded.py
Loads curated signal fixtures from `data/seed_signals/*.json` for every non-GitHub source used in the demo; fixture shape mirrors exactly what a live scraper for that source would emit so a real scraper can later be swapped in without changing downstream code. No external network calls or env vars.

- `SeededScraper` — implements `BaseScraper` by reading signals from a JSON fixture file instead of a live source.
  - `SeededScraper.__init__(fixture_path)` — stores the fixture file path and derives the scraper's `name` from the file stem.
  - `SeededScraper.scrape() -> list[Signal]` — returns `[]` if the fixture file doesn't exist; otherwise parses the JSON file's `signals` array into `Signal` records, defaulting each record's `source`/`signal_category` to the fixture's top-level `source`/`category` (or the file stem) when not specified per-row.

## backend/scrapers/semantic_scholar.py
Scrapes the free, unauthenticated Semantic Scholar Graph API (author search -> papers -> co-authors) to emit co-authored-paper signals and co-author graph edges for discovery-cohort people with real (full) names. No API key/env var required; the client backs off and retries on HTTP 429 rate-limiting and fails soft.

- `SemanticScholarClient` — thin wrapper around the Semantic Scholar Graph API with retry/backoff on rate limiting; all failures (including persistent 429s) return `None`/`[]`.
  - `SemanticScholarClient.__init__(max_retries=3, backoff_seconds=2.0)` — sets up a `requests.Session` with a descriptive User-Agent and configures retry count/backoff.
  - `SemanticScholarClient._get(path, params=None)` — issues a GET request, retrying with linearly increasing backoff on HTTP 429 up to `max_retries` times, returning parsed JSON or `None` on any other failure or exhausted retries.
  - `SemanticScholarClient.search_author(name) -> list[dict]` — searches for authors by name, returning candidate author records with name/paperCount/hIndex/url.
  - `SemanticScholarClient.author_papers(author_id, limit=10) -> list[dict]` — fetches an author's papers (title, year, url, authors) up to `limit`.
- `SemanticScholarScraper` — per-person collector that resolves a person to a Semantic Scholar author and emits co-authorship signals/edges; capped so one person costs at most 2 API calls.
  - `SemanticScholarScraper.__init__(client=None, max_papers=3, max_coauthors_per_paper=5)` — stores (or default-constructs) a `SemanticScholarClient` and caps on papers/co-authors processed per person.
  - `SemanticScholarScraper.has_real_name(person) -> bool` (static) — returns whether a person has a plausible full name (contains a space, and isn't identical to their GitHub login) suitable for author search, avoiding false matches from bare usernames.
  - `SemanticScholarScraper.find_author(name) -> dict | None` — searches for an author by name and returns the single normalized-name-exact match whose paper count is between 1 and `MAX_AUTHOR_PAPERS` (50), treating any ambiguous (multiple matches) or overly prolific (established academic) result as no match.
  - `SemanticScholarScraper.collect(person, author=None) -> tuple[list[Signal], list[GraphEdge]]` — for a person with a real name, resolves (or reuses) their author record, then for up to `max_papers` co-authored papers (skipping solo papers with no co-authors) emits a `co_authored_paper` signal (strength 0.6) per paper and a `co_author` graph edge to up to `max_coauthors_per_paper` co-authors per paper.
