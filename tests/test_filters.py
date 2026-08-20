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
