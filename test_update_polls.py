import pandas as pd
import unittest

from update_polls import clean_cell, parse_date, parse_percent


class TestUpdatePolls(unittest.TestCase):
    def setUp(self):
        # Prepare any shared test data here
        self.sample_cell = "'''65%'''"

    def tearDown(self):
        # Clean up any resources if needed (currently none)
        pass

    def test_clean_cell(self):
        self.assertEqual(clean_cell(self.sample_cell), "65%")

    def test_parse_date(self):
        result = parse_date("{{dts|October 21, 2026}}")
        self.assertEqual(result, pd.Timestamp("2026-10-21"))

    def test_parse_percent(self):
        self.assertEqual(parse_percent("65%"), "65%")
