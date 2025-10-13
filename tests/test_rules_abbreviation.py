from mkdocs_french.rules.abbreviation import det_abbreviation, fix_abbreviation


def test_fix_abbreviation_normalizes_etc_variants():
    text = "etc.. etc... etc.... ETC... EtC…"
    expected = "etc. etc. etc. ETC. Etc."
    assert fix_abbreviation(text) == expected


def test_det_abbreviation_reports_extra_punctuation_after_etc():
    issues = det_abbreviation("Il viendra, etc...")
    assert any("Ponctuation superflue après «etc" in issue[2] for issue in issues)
    assert any(issue[3] == "etc." for issue in issues)
