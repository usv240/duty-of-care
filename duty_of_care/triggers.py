from __future__ import annotations

import re

from .models import Scene, Trigger


_HEADING = re.compile(r"(?m)^(INT\.|EXT\.|INT/EXT\.|I/E\.)[^\n]+$")
_SUBJECT = re.compile(r"\b(?:suicid\w*|self[- ]harm\w*|overdos\w*|relaps\w*|addiction)\b", re.I)
_METHOD_DETAIL = re.compile(r"\b(?:dosage|exact amount|step[- ]by[- ]step|where to obtain|procure[sd]?|specific method)\b", re.I)
_SOLUTION = re.compile(r"\b(?:only way out|solves everything|finally free|all problems end|revenge is complete)\b", re.I)
_HELP = re.compile(r"\b(?:asks? for help|calls? a friend|counsell?or|therapist|support|intervenes?|recovery|coping|hotline|crisis line)\b", re.I)
_ROMANTIC = re.compile(r"\b(?:beautiful sacrifice|heroic act|perfect revenge|glorious|idealised memorial)\b", re.I)
_SIGNPOST = re.compile(r"\b(?:988|crisis resource|support resource|help is available)\b", re.I)


def parse_scenes(screenplay: str) -> list[Scene]:
    matches = list(_HEADING.finditer(screenplay))
    if not matches:
        return [Scene(scene_id="scene-001", heading="UNFORMATTED SCENE", text=screenplay.strip())]
    scenes = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(screenplay)
        scenes.append(Scene(scene_id=f"scene-{index + 1:03d}", heading=match.group(0).strip(), text=screenplay[match.end():end].strip()))
    return scenes


def _excerpt(text: str, match: re.Match[str]) -> str:
    start = max(0, match.start() - 60)
    end = min(len(text), match.end() + 60)
    return " ".join(text[start:end].split())


def detect_triggers(screenplay: str) -> list[Trigger]:
    scenes = parse_scenes(screenplay)
    triggers: list[Trigger] = []
    subject_scenes = []
    for scene in scenes:
        subject = _SUBJECT.search(scene.text)
        if not subject:
            continue
        subject_scenes.append(scene.scene_id)
        for trigger_class, pattern, rule in (
            ("method_specificity", _METHOD_DETAIL, "A candidate contains procedural, procurement, location, or quantity specificity."),
            ("framing_as_solution", _SOLUTION, "The act occurs near language framing it as a solution or completed revenge."),
            ("romanticisation", _ROMANTIC, "The scene contains idealising or memorialising language."),
        ):
            match = pattern.search(scene.text)
            if match:
                triggers.append(Trigger(scene_id=scene.scene_id, trigger_class=trigger_class, evidence_excerpt=_excerpt(scene.text, match), rule=rule, matched_text=match.group(0), match_start=match.start(), match_end=match.end()))
        if not _HELP.search(scene.text):
            triggers.append(Trigger(scene_id=scene.scene_id, trigger_class="absence_of_help_seeking", evidence_excerpt=_excerpt(scene.text, subject), rule="The candidate scene mentions the subject without a nearby support, intervention, coping, or aftermath signal.", matched_text=subject.group(0), match_start=subject.start(), match_end=subject.end()))

    if len(subject_scenes) >= 2:
        for scene_id in subject_scenes:
            triggers.append(Trigger(scene_id=scene_id, trigger_class="repetition", evidence_excerpt=f"Subject appears in {len(subject_scenes)} scenes.", rule="The same act or subject is depicted repeatedly across the script."))
    if subject_scenes and not _SIGNPOST.search(screenplay):
        triggers.append(Trigger(scene_id="document", trigger_class="signposting_absence", evidence_excerpt="No resource signpost detected in the screenplay.", rule="The document contains a candidate scene but no support-resource reference."))
    return triggers
