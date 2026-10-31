
import pandas as pd

from update_polls import clean_cell, parse_date, parse_percent


def test_clean_cell():
    assert clean_cell("'''65%'''") == "65%"


def test_parse_date():
    result = parse_date("{{dts|October 21, 2026}}")
    assert result == pd.Timestamp("2026-10-21")


def test_parse_percent():
    assert parse_percent("65%") == "65%"
