"""Re-run contact + location enrichment over everyone already in the DB.

No network calls — it re-reads each person's stored GitHub profile signals, so
it's safe to run after tweaking the enricher. Then rescores. Prints LinkedIn yield.
Run: python scripts/reenrich.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.container import Container


def main() -> None:
    container = Container()
    people = [p for p in container.persons.all() if p.cohort != "control"]
    with_linkedin = 0
    for person in people:
        sigs = container.signals.for_person(person.id)
        container.contact_enricher.enrich(person, sigs)
        container.location_resolver.resolve(person, sigs)
        container.persons.save(person)
        if person.linkedin_url:
            with_linkedin += 1
    container.candidate_service.rescore_all()

    discoveries = [p for p in people if p.cohort == "discovery"]
    disc_linkedin = [p for p in discoveries if p.linkedin_url]
    print(f"re-enriched {len(people)} people; {with_linkedin} have a real LinkedIn URL")
    print(f"discoveries: {len(disc_linkedin)}/{len(discoveries)} now carry a resolved LinkedIn profile")
    for p in sorted(disc_linkedin, key=lambda p: -(p.score or 0))[:15]:
        src = p.contact_info.get("linkedin_source", "?")
        print(f"  {p.name:<28} {p.linkedin_url}  [{src}]")


if __name__ == "__main__":
    main()
