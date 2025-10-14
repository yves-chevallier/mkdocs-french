from mkdocs_french.constants import ELLIPSIS, NBSP, NNBSP
from mkdocs_french.rules.spacing import det_spacing, fix_spacing


def test_fix_spacing_inserts_non_breaking_spaces():
    text = "Bonjour: test; oui? non!"
    result = fix_spacing(text)
    assert result == f"Bonjour{NBSP}: test{NNBSP}; oui{NNBSP}? non{NNBSP}!"


def test_fix_spacing_converts_ellipsis_and_apostrophes():
    text = "L'homme a dit..."
    assert fix_spacing(text) == f"L’homme a dit{ELLIPSIS}"


def test_fix_spacing_removes_terminal_period_and_comma_before_ellipsis():
    text = "Tu reviens?. Oui!. m, ..."
    expected = f"Tu reviens{NNBSP}? Oui{NNBSP}! m{ELLIPSIS}"
    assert fix_spacing(text) == expected


def test_fix_spacing_converts_double_hyphen_to_em_dash():
    text = "Bonjour -- comment allez-vous?"
    expected = f"Bonjour — comment allez-vous{NNBSP}?"
    assert fix_spacing(text) == expected


def test_det_spacing_reports_new_spacing_issues():
    issues = det_spacing("Tu reviens?. m, ... -- voilà")
    messages = [issue[2] for issue in issues]
    assert any("Ponctuation finale superflue" in msg for msg in messages)
    assert any("Virgule superflue avant ellipse" in msg for msg in messages)
    assert any("tiret cadratin" in msg.lower() for msg in messages)
