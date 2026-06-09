from src.narrative_patterns import filter_person_names, is_valid_person_name


def test_filter_non_person_words() -> None:
    names = filter_person_names(["羅恩", "立刻", "艾琳", "第一"])
    assert "羅恩" in names
    assert "艾琳" in names
    assert "立刻" not in names
    assert "第一" not in names
    assert not is_valid_person_name("立刻")
