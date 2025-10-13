from __future__ import annotations

import pytest

from mkdocs_french.rules import ordinaux


def test_det_ordinaux_detects_various_suffixes():
    text = "1ère place, 2ieme test, 3èmes essais, 7IEMES cas, 5res"

    replacements = {preview for *_rest, preview in ordinaux.det_ordinaux(text)}

    assert replacements == {"1^re^", "2^e^", "3^es^", "7^es^"}


def test_fix_ordinaux_converts_matches():
    text = "1ere 2ieme 4ème"

    assert ordinaux.fix_ordinaux(text) == "1^re^ 2^e^ 4^e^"


@pytest.mark.parametrize(
    ("number", "suffix", "expected"),
    [
        ("1", "ème", "er"),
        ("1", "ères", "res"),
        ("2", "ieme", "e"),
        ("12", "iemes", "es"),
        ("3", "ires", None),
    ],
)
def test_normalize_suffix_cases(number, suffix, expected):
    assert ordinaux._normalize_suffix(number, suffix) == expected
