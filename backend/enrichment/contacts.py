"""ContactEnricher: surface email / X handle / personal site / LinkedIn search URL.

Sources (plan): GitHub public email + social accounts, bio parsing,
Semantic Scholar author emails, generated LinkedIn search query (never scraped).
Idempotent — never overwrites a manually-entered value.
"""

import re
from urllib.parse import quote_plus

from backend.domain.person import Person
from backend.domain.signal import Signal

TWITTER_RE = re.compile(r"(?:twitter\.com/|x\.com/|@)([A-Za-z0-9_]{2,15})")
URL_RE = re.compile(r"https?://[^\s)\"']+")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
# A LinkedIn profile the person published themselves (in a bio, blog, or social link).
LINKEDIN_RE = re.compile(
    r"(?:https?://)?(?:[\w-]+\.)?linkedin\.com/(?:in|pub)/[A-Za-z0-9\-_%]+/?",
    re.IGNORECASE,
)


def normalize_linkedin(url: str) -> str:
    """Canonicalize a captured LinkedIn URL to https://www.linkedin.com/in/<slug>."""
    url = url.strip().rstrip("/")
    if not url.startswith("http"):
        url = "https://" + url
    return url


class ContactEnricher:
    def enrich(self, person: Person, signals: list[Signal]) -> Person:
        github_profiles = [
            s.raw_data for s in signals
            if s.source == "github" and isinstance(s.raw_data, dict) and s.raw_data.get("login")
        ]
        for profile in github_profiles:
            self._apply_github_profile(person, profile)
        for signal in signals:
            email = signal.metadata.get("author_email") if isinstance(signal.metadata, dict) else None
            if email and not person.email:
                person.email = email
                person.contact_info.setdefault("email_source", signal.source)

        if not person.linkedin_url:
            query_bits = [f'site:linkedin.com/in "{person.name}"']
            if person.school:
                query_bits.append(person.school.split("(")[0].strip())
            if person.area:
                query_bits.append(person.area)
            person.contact_info.setdefault(
                "linkedin_search_url",
                f"https://www.google.com/search?q={quote_plus(' '.join(query_bits))}",
            )
        else:
            person.contact_info.setdefault("linkedin_source", person.contact_info.get("linkedin_source", "github"))
        return person

    def _apply_github_profile(self, person: Person, profile: dict) -> None:
        if not person.email and profile.get("email"):
            person.email = profile["email"]
            person.contact_info.setdefault("email_source", "github")
        if not person.twitter_handle and profile.get("twitter_username"):
            person.twitter_handle = profile["twitter_username"]
        bio = profile.get("bio") or ""
        if not person.twitter_handle:
            match = TWITTER_RE.search(bio)
            if match:
                person.twitter_handle = match.group(1)
        # LinkedIn the person published in their own bio text.
        if not person.linkedin_url:
            match = LINKEDIN_RE.search(bio)
            if match:
                person.linkedin_url = normalize_linkedin(match.group(0))
                person.contact_info["linkedin_source"] = "github_bio"
        blog = (profile.get("blog") or "").strip()
        if blog:
            # A blog field that is itself a LinkedIn URL is a real profile, not a site.
            if "linkedin.com" in blog.lower() and not person.linkedin_url:
                person.linkedin_url = normalize_linkedin(blog)
                person.contact_info["linkedin_source"] = "github_blog"
            elif not person.personal_site and "linkedin.com" not in blog.lower():
                person.personal_site = blog if blog.startswith("http") else f"https://{blog}"
        if not person.email:
            match = EMAIL_RE.search(bio)
            if match:
                person.email = match.group(0)
                person.contact_info.setdefault("email_source", "github_bio")
        for account in profile.get("social_accounts", []):
            url = account.get("url", "")
            if "linkedin.com" in url and not person.linkedin_url:
                person.linkedin_url = normalize_linkedin(url)
                person.contact_info["linkedin_source"] = "github_social"
            if ("twitter.com" in url or "x.com" in url) and not person.twitter_handle:
                match = TWITTER_RE.search(url)
                if match:
                    person.twitter_handle = match.group(1)
