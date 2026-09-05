"""Layer one: deterministic candidate selection over the parsed screenplay.

Pure code, no model. Every trigger carries the exact phrase, its character
offsets, and the rule that fired, so a writer can audit why a scene became a
candidate. A trigger is not a flag: retrieval decides whether an applicable,
source-linked clause exists, and the writer decides what to do with it.
"""

from __future__ import annotations

import re

from .models import Scene, Trigger

DOCUMENT_SCENE_ID = "document"

_HEADING = re.compile(r"(?m)^(INT\.|EXT\.|INT/EXT\.|I/E\.)[^\n]+$")
_SUBJECT = re.compile(
    r"\b(?:suicid\w*|self[- ]harm\w*|overdos\w*|relaps\w*|addiction)\b", re.IGNORECASE
)
_METHOD_DETAIL = re.compile(
    r"\b(?:dosage|exact amount|step[- ]by[- ]step|where to obtain|where it could be obtained|"
    r"procure[sd]?|specific method)\b",
    re.IGNORECASE,
)
_SOLUTION = re.compile(
    r"\b(?:only way out|only way to make|solves everything|finally free|all problems end|"
    r"revenge is complete|finally understand)\b",
    re.IGNORECASE,
)
_HELP = re.compile(
    r"\b(?:asks? for help|calls? a friend|calls? someone|counsell?or|therapist|support|"
    r"intervenes?|recovery|coping|hotline|crisis line|helpline|lifeline|samaritans|sponsor|"
    r"meetings?|sit(?:s)? with|stay(?:s|ed|ing)? (?:with|beside|here|until)|"
    r"talk to someone|someone who knows|ring (?:it|the line))\b",
    re.IGNORECASE,
)
_ROMANTIC = re.compile(
    r"\b(?:beautiful sacrifice|heroic act|perfect revenge|glorious|idealised memorial|"
    r"chose peace|at peace now|bravest thing|did it for us)\b",
    re.IGNORECASE,
)
_SIGNPOST = re.compile(
    r"\b(?:988|9-8-8|116 123|crisis resource|support resource|help is available|"
    r"helpline|samaritans\.org|findahelpline)\b",
    re.IGNORECASE,
)

_SCENE_RULES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "method_specificity",
        _METHOD_DETAIL,
        "A candidate contains procedural, procurement, location, or quantity specificity.",
    ),
    (
        "framing_as_solution",
        _SOLUTION,
        "The act occurs near language framing it as a solution or completed revenge.",
    ),
    (
        "romanticisation",
        _ROMANTIC,
        "The scene contains idealising or memorialising language.",
    ),
)


def parse_scenes(screenplay: str) -> list[Scene]:
    matches = list(_HEADING.finditer(screenplay))
    if not matches:
        return [Scene(scene_id="scene-001", heading="UNFORMATTED SCENE", text=screenplay.strip())]
    scenes = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(screenplay)
        scenes.append(
            Scene(
                scene_id=f"scene-{index + 1:03d}",
                heading=match.group(0).strip(),
                text=screenplay[match.end() : end].strip(),
            )
        )
    return scenes


def _excerpt(text: str, match: re.Match[str]) -> str:
    start = max(0, match.start() - 60)
    end = min(len(text), match.end() + 60)
    return " ".join(text[start:end].split())


def _trigger(scene: Scene, klass: str, match: re.Match[str], rule: str) -> Trigger:
    return Trigger(
        scene_id=scene.scene_id,
        trigger_class=klass,  # type: ignore[arg-type]
        evidence_excerpt=_excerpt(scene.text, match),
        rule=rule,
        matched_text=match.group(0),
        match_start=match.start(),
        match_end=match.end(),
    )


def detect_triggers(screenplay: str) -> list[Trigger]:
    scenes = parse_scenes(screenplay)
    triggers: list[Trigger] = []
    subject_scenes: list[str] = []
    candidate_scenes: list[str] = []
    for scene in scenes:
        subject = _SUBJECT.search(scene.text)
        if not subject:
            continue
        subject_scenes.append(scene.scene_id)
        before = len(triggers)
        for trigger_class, pattern, rule in _SCENE_RULES:
            match = pattern.search(scene.text)
            if match:
                triggers.append(_trigger(scene, trigger_class, match, rule))
        if not _HELP.search(scene.text):
            triggers.append(
                _trigger(
                    scene,
                    "absence_of_help_seeking",
                    subject,
                    "The candidate scene mentions the subject without a nearby support, "
                    "intervention, coping, or aftermath signal.",
                )
            )
        if len(triggers) > before:
            candidate_scenes.append(scene.scene_id)

    # Repetition is about the act being depicted again without aftermath, not about
    # a subject being discussed in several scenes. Only scenes that are already
    # candidates count, so a recovery storyline that names relapse in every scene
    # is not treated as repeated depiction.
    if len(candidate_scenes) >= 2:
        for scene_id in candidate_scenes:
            triggers.append(
                Trigger(
                    scene_id=scene_id,
                    trigger_class="repetition",
                    evidence_excerpt=(
                        f"Candidate depiction appears in {len(candidate_scenes)} scenes."
                    ),
                    rule="The same act or subject is depicted repeatedly across the script "
                    "without a support or aftermath signal.",
                )
            )
    if subject_scenes and not _SIGNPOST.search(screenplay):
        triggers.append(
            Trigger(
                scene_id=DOCUMENT_SCENE_ID,
                trigger_class="signposting_absence",
                evidence_excerpt="No resource signpost detected in the screenplay.",
                rule="The document contains a candidate scene but no support-resource reference.",
            )
        )
    return triggers


def document_scene(screenplay: str) -> Scene:
    """A pseudo-scene so document-level triggers can be grounded like any other."""
    return Scene(
        scene_id=DOCUMENT_SCENE_ID,
        heading="WHOLE DOCUMENT",
        text=screenplay.strip()[:6000],
    )
