from __future__ import annotations

REGIONS: dict[str, str] = {
    "US": "United States",
    "GB": "United Kingdom",
    "CA": "Canada",
    "AU": "Australia",
}

RESOURCES = {
    "US": {"name": "988 Suicide & Crisis Lifeline", "contact": "Call or text 988", "url": "https://988lifeline.org/"},
    "CA": {"name": "9-8-8 Suicide Crisis Helpline", "contact": "Call or text 9-8-8", "url": "https://988.ca/"},
    "GB": {"name": "Samaritans", "contact": "Call 116 123", "url": "https://www.samaritans.org/how-we-can-help/contact-samaritan/"},
    "AU": {"name": "Lifeline Australia", "contact": "Call 13 11 14", "url": "https://www.lifeline.org.au/"},
}

FIND_A_HELPLINE = {"name": "Find A Helpline", "contact": "Search by country", "url": "https://findahelpline.com/"}


def resources_for(region: str) -> list[dict[str, str]]:
    selected = RESOURCES.get(region.upper(), RESOURCES["US"])
    return [selected, FIND_A_HELPLINE]


def known_region(region: str) -> bool:
    return region.upper() in REGIONS
