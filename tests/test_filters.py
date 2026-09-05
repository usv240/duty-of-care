import pytest

from duty_of_care.filters import DISCLAIMER, validate_rendered_text, validate_suggestion


def test_never_says_safe():
    with pytest.raises(ValueError):
        validate_rendered_text("Your scene is safe.")
    assert "not clinical or professional certification" in validate_rendered_text(DISCLAIMER)


def test_rejects_added_specificity():
    with pytest.raises(ValueError):
        validate_suggestion("The character is distressed.", "Add an exact amount to the scene.")


def test_allows_less_specific_rewrite():
    assert validate_suggestion("The scene states an exact amount.", "The scene omits procedural detail.")


def test_output_filter_compares_specificity_on_the_alternative_only():
    from duty_of_care_agent.agent import ALTERNATIVE_HEADING, WITHHELD, apply_output_filter

    scene = "INT. ROOM - NIGHT\nA character mentions suicide."
    explanation = (
        "Why this guidance may apply\n\nThe publisher's clause about avoiding a specific method "
        f"applies here.\n\n{ALTERNATIVE_HEADING}\n\nA friend stays and they ring the line."
    )
    text, status = apply_output_filter(scene, explanation)
    assert status == "passed" and text == explanation

    leaky = f"Why\n\n{ALTERNATIVE_HEADING}\n\nShe recites the exact amount and the dosage."
    text, status = apply_output_filter(scene, leaky)
    assert status == "rejected" and text == WITHHELD

    certifying = f"Your scene is safe.\n\n{ALTERNATIVE_HEADING}\n\nA friend stays."
    assert apply_output_filter(scene, certifying)[1] == "rejected"


def test_output_filter_trusts_a_draft_the_tool_accepted_verbatim():
    from duty_of_care_agent.agent import ALTERNATIVE_HEADING, WITHHELD, apply_output_filter

    scene = "INT. ROOM - NIGHT\nA character mentions self-harm, then the scene ends."
    draft = "She says she will not give the specific method any more room tonight; a friend stays."
    closing = "The writer may accept, dismiss, or ask for expert review."
    text = f"Why\n\n{ALTERNATIVE_HEADING}\n\n{draft}\n\n{closing}"
    assert apply_output_filter(scene, text)[1] == "rejected"
    assert apply_output_filter(scene, text, [draft])[1] == "passed"
    longer = text.replace(draft, draft + " She lists the dosage.")
    assert apply_output_filter(scene, longer, [draft])[0] == WITHHELD
    certifying = f"Your scene is safe.\n\n{ALTERNATIVE_HEADING}\n\n{draft}"
    assert apply_output_filter(scene, certifying, [draft])[1] == "rejected"
