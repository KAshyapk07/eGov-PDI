from reconcile import name_match


def test_normalize_strips_accents_case_and_punctuation():
    assert name_match.normalize("Am-Timan") == "am timan"
    assert name_match.normalize("Moungoultyé") == "moungoultye"
    assert name_match.normalize(None) == ""


def test_exact_match_ignores_accents_and_case():
    pairs, left_only, right_only = name_match.match_names(["ADRE", "ABECHE"], ["Adre", "Abeche"])

    assert {(p["left"], p["right"], p["kind"]) for p in pairs} == {
        ("ADRE", "Adre", "exact"), ("ABECHE", "Abeche", "exact")}
    assert left_only == [] and right_only == []


def test_fuzzy_match_pairs_close_spellings_and_reports_leftovers():
    pairs, left_only, right_only = name_match.match_names(
        ["PONT KAROL", "ZZZTOWN"], ["Pont Carol", "Faya"], fuzzy_cutoff=0.82)

    fuzzy = [p for p in pairs if p["kind"] == "fuzzy"]
    assert len(fuzzy) == 1
    assert fuzzy[0]["left"] == "PONT KAROL" and fuzzy[0]["right"] == "Pont Carol"
    assert left_only == ["ZZZTOWN"]
    assert right_only == ["Faya"]


def test_match_is_one_to_one():
    pairs, left_only, right_only = name_match.match_names(["Mao", "Mao"], ["Mao"])

    assert len([p for p in pairs if p["kind"] == "exact"]) == 1
    assert left_only == [] and right_only == []
