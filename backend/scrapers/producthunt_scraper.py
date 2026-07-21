"""Product Hunt maker scraper. PH's leaderboard/product pages are JS-rendered
SPAs and actively bot-fingerprinted, so this is the one free source that
needs an actual browser — every other free-source scraper
(fellowship_scraper.py, competition_scraper.py) gets by with a plain GET via
ConfigSourceScraper. Playwright renders each page; parsing past that point is
plain regex over the rendered HTML, same fail-soft convention as the rest of
backend/scrapers/.

Two-level crawl: a leaderboard page lists product links but no maker names;
each product page lists its makers as PH-internal profile links (/@username)
with no external LinkedIn/GitHub/site exposed. That profile link is still a
stable per-person identifier, so it's carried as `personal_site` on the
RawLead — lead_extraction's "needs a nearby link" convention and
LeadResolver's PDL-Identify fallback both work on it unmodified, no schema
change required.
"""

import json
import logging
import re
from pathlib import Path
from urllib.parse import urljoin

from backend.scrapers.config_scraper import USER_AGENT
from backend.scrapers.resolve import RawLead

logger = logging.getLogger(__name__)

BASE = "https://www.producthunt.com"
PRODUCT_LINK_RE = re.compile(r'href="(/(?:posts|products)/[a-z0-9\-]+)"')
MAKER_RE = re.compile(r'href="(/@[A-Za-z0-9_\-]+)"[^>]*>\s*([^<]{2,80}?)\s*</a>')
NAME_RE = re.compile(r"^[A-Z][a-zA-Z'\-]+(?:\s[A-Z][a-zA-Z'\-]+){1,2}$")


class ProductHuntScraper:
    """Renders leaderboard + product pages with Playwright, then hands the
    rendered HTML to plain-regex parsing. Playwright import is lazy so an
    environment without the browser installed degrades to zero leads instead
    of an import crash at container-wiring time."""

    name = "producthunt"

    def __init__(self, sources_file: Path, max_products_per_source: int = 10):
        self.sources_file = sources_file
        self.max_products_per_source = max_products_per_source

    def scrape(self, source_id: str | None = None, max_products_per_source: int | None = None) -> list[RawLead]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.warning("producthunt scraper skipped: playwright not installed")
            return []

        limit = max_products_per_source or self.max_products_per_source
        sources = self._sources()
        leads: list[RawLead] = []
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                try:
                    context = browser.new_context(user_agent=USER_AGENT)
                    for source in sources:
                        if source_id and source["id"] != source_id:
                            continue
                        leads.extend(self._scrape_source(context, source, limit))
                finally:
                    browser.close()
        except Exception as exc:  # Playwright's own exception hierarchy, not requests'
            logger.warning("producthunt scrape failed: %s", exc)
            return leads
        return leads

    def _scrape_source(self, context, source: dict, limit: int) -> list[RawLead]:
        html = self._render(context, source["url"])
        if not html:
            return []
        leads: list[RawLead] = []
        for product_url in self._product_urls(html, source["url"])[:limit]:
            product_html = self._render(context, product_url)
            if not product_html:
                continue
            leads.extend(self._makers(product_html, source["id"], product_url))
        return leads

    def _render(self, context, url: str) -> str | None:
        try:
            page = context.new_page()
            try:
                page.goto(url, timeout=20000, wait_until="networkidle")
                return page.content()
            finally:
                page.close()
        except Exception as exc:
            logger.warning("producthunt render failed %s: %s", url, exc)
            return None

    @staticmethod
    def _product_urls(html: str, base_url: str) -> list[str]:
        seen: list[str] = []
        for path in PRODUCT_LINK_RE.findall(html):
            url = urljoin(base_url, path)
            if url not in seen:
                seen.append(url)
        return seen

    @staticmethod
    def _makers(html: str, source_id: str, product_url: str) -> list[RawLead]:
        leads: list[RawLead] = []
        seen: set[str] = set()
        for path, text in MAKER_RE.findall(html):
            name = text.strip()
            if not NAME_RE.match(name):
                continue
            key = path.lower()
            if key in seen:
                continue
            seen.add(key)
            leads.append(RawLead(
                name=name, source=source_id, source_url=product_url,
                personal_site=urljoin(BASE, path),
            ))
        return leads

    def _sources(self) -> list[dict]:
        try:
            return json.loads(self.sources_file.read_text()).get("sources", [])
        except (OSError, ValueError) as exc:
            logger.warning("producthunt sources file unavailable (%s): %s", self.sources_file, exc)
            return []
