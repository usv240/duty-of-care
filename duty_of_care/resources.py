from __future__ import annotations


RESOURCES = {
    "US": {"name": "988 Suicide & Crisis Lifeline", "contact": "Call or text 988", "url": "https://988lifeline.org/"},
    "CA": {"name": "9-8-8 Suicide Crisis Helpline", "contact": "Call or text 9-8-8", "url": "https://988.ca/"},
    "GB": {"name": "Samaritans", "contact": "Call 116 123", "url": "https://www.samaritans.org/how-we-can-help/contact-samaritan/"},
}


def resources_for(region: str) -> list[dict[str, str]]:
    selected = RESOURCES.get(region.upper(), RESOURCES["US"])
    return [selected, {"name": "Find A Helpline", "contact": "Search by country", "url": "https://findahelpline.com/"}]
