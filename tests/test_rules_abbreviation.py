from mkdocs_french.rules.abbreviation import AbbreviationRule


rule = AbbreviationRule()


def test_fix_abbreviation_normalizes_etc_variants():
    text = "etc.. etc... etc.... ETC... EtC…"
    expected = "etc. etc. etc. ETC. Etc."
    assert rule.fix(text) == expected


def test_det_abbreviation_reports_extra_punctuation_after_etc():
    issues = rule.detect("Il viendra, etc...")
    assert any("Ponctuation superflue après «etc" in issue[2] for issue in issues)
    assert any(issue[3] == "etc." for issue in issues)
