from duty_of_care.triggers import detect_triggers


def classes(text: str) -> set[str]:
    return {item.trigger_class for item in detect_triggers(text)}


def test_method_specificity_candidate():
    text = "INT. ROOM - NIGHT\nA character discusses suicide with an exact amount."
    assert "method_specificity" in classes(text)


def test_help_seeking_avoids_absence_trigger():
    text = "INT. KITCHEN - DAY\nAfter self-harm thoughts, Maya calls a friend and asks for help."
    assert "absence_of_help_seeking" not in classes(text)


def test_neutral_non_subject_scene_has_no_triggers():
    assert detect_triggers("EXT. PARK - DAY\nMaya repairs a bicycle with her sister.") == []


def test_repetition_is_document_level_signal():
    text = "INT. ROOM - NIGHT\nA character mentions self-harm.\nEXT. PARK - DAY\nThey discuss self-harm again."
    assert "repetition" in classes(text)


def test_signposting_absence_and_presence():
    absent = "INT. ROOM - NIGHT\nA character mentions suicide."
    present = absent + "\nSUPER: Help is available. Call 988."
    assert "signposting_absence" in classes(absent)
    assert "signposting_absence" not in classes(present)
