"""Product Hunt scraper: pure-parse coverage for the regex logic that runs on
Playwright-rendered HTML, plus the fail-soft path when Playwright itself isn't
installed. Real browser rendering is exercised live, not in this suite --
same boundary ConfigSourceScraper draws around requests.Session.
"""

import tempfile
import unittest
from pathlib import Path

from backend.scrapers.producthunt_scraper import ProductHuntScraper


class ProductUrlsTests(unittest.TestCase):
    def test_extracts_post_and_product_links(self):
        html = """
        <a href="/posts/some-app">Some App</a>
        <a href="/products/other-app">Other App</a>
        """
        urls = ProductHuntScraper._product_urls(html, "https://www.producthunt.com/")
        self.assertEqual(
            urls,
            ["https://www.producthunt.com/posts/some-app", "https://www.producthunt.com/products/other-app"],
        )

    def test_deduplicates_repeated_links(self):
        html = '<a href="/posts/app">A</a><a href="/posts/app">A again</a>'
        urls = ProductHuntScraper._product_urls(html, "https://www.producthunt.com/")
        self.assertEqual(len(urls), 1)

    def test_no_product_links_returns_empty(self):
        self.assertEqual(ProductHuntScraper._product_urls("<p>nothing here</p>", "https://www.producthunt.com/"), [])


class MakersTests(unittest.TestCase):
    def test_extracts_maker_name_and_profile_link(self):
        html = '<a href="/@adalovelace">Ada Lovelace</a>'
        leads = ProductHuntScraper._makers(html, "producthunt_today", "https://www.producthunt.com/posts/app")
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0].name, "Ada Lovelace")
        self.assertEqual(leads[0].personal_site, "https://www.producthunt.com/@adalovelace")
        self.assertEqual(leads[0].source, "producthunt_today")
        self.assertEqual(leads[0].source_url, "https://www.producthunt.com/posts/app")
        self.assertIsNone(leads[0].linkedin_url)

    def test_non_name_link_text_is_skipped(self):
        html = '<a href="/@adalovelace">Follow</a>'
        leads = ProductHuntScraper._makers(html, "producthunt_today", "https://www.producthunt.com/posts/app")
        self.assertEqual(leads, [])

    def test_duplicate_maker_on_one_page_is_deduped(self):
        html = '<a href="/@ada">Ada Lovelace</a> ... <a href="/@ada">Ada Lovelace</a>'
        leads = ProductHuntScraper._makers(html, "producthunt_today", "https://www.producthunt.com/posts/app")
        self.assertEqual(len(leads), 1)

    def test_no_maker_links_returns_empty(self):
        self.assertEqual(
            ProductHuntScraper._makers("<p>no makers listed</p>", "producthunt_today", "https://www.producthunt.com/posts/app"),
            [],
        )


class ScrapeFailSoftTests(unittest.TestCase):
    def _sources_file(self, sources) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = Path(temp_dir.name) / "sources.json"
        import json
        path.write_text(json.dumps({"sources": sources}))
        return path

    def test_missing_sources_file_is_fail_soft(self):
        scraper = ProductHuntScraper(Path("/nonexistent/sources.json"))
        self.assertEqual(scraper._sources(), [])

    def test_scrape_without_playwright_installed_returns_empty(self):
        # This repo's test env has no playwright installed -- scrape() must
        # degrade to [] rather than raise ImportError.
        sources_file = self._sources_file([{"id": "producthunt_today", "url": "https://www.producthunt.com/"}])
        scraper = ProductHuntScraper(sources_file)
        self.assertEqual(scraper.scrape(), [])


if __name__ == "__main__":
    unittest.main()
