from __future__ import annotations

import re


_FORBIDDEN_CERTIFICATION = re.compile(r"\b(?:your (?:scene|script) is safe|certified safe|clinically safe|no risk)\b", re.I)
_SPECIFICITY = re.compile(r"\b(?:dosage|exact amount|step[- ]by[- ]step|where to obtain|procure[sd]?|specific method|brand|address)\b", re.I)


DISCLAIMER = "No additional guidance conflicts were detected by this pre-review. This is not clinical or professional certification."


def specificity_score(text: str) -> int:
    return len(_SPECIFICITY.findall(text)) + len(re.findall(r"\b\d+(?:\.\d+)?\s*(?:mg|ml|grams?)\b", text, re.I))


def validate_suggestion(original: str, proposed: str) -> str:
    if _FORBIDDEN_CERTIFICATION.search(proposed):
        raise ValueError("suggestion contains prohibited safety-certification language")
    if specificity_score(proposed) > specificity_score(original):
        raise ValueError("suggestion introduces more method specificity than the source")
    return proposed


def validate_rendered_text(text: str) -> str:
    if _FORBIDDEN_CERTIFICATION.search(text):
        raise ValueError("rendered output contains prohibited safety-certification language")
    return text
