from __future__ import annotations

from mkdocs_french.rules import units


def test_units_detector_identifies_missing_spacing():
    text = "Il fait 20°C et 50kg de charge, soit 10kWh."
    results = units.det_units(text)
    messages = [result[2] for result in results]
    assert "Unités : «20°C»" in messages[0]
    assert "Unités : «50kg»" in messages[1]
    assert "Unités : «10kWh»" in messages[2]


def test_units_fix_inserts_narrow_nbsp():
    text = "20°C, 50kg et 10kWh"
    fixed = units.fix_units(text)
    assert "20 °C" in fixed
    assert "50 kg" in fixed
    assert "10 kWh" in fixed
