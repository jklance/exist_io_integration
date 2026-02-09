"""Tests for value formatting."""

import pytest

from exist_backup.formatting import format_value


class TestFormatValue:
    def test_integer(self):
        assert format_value("8432", 0) == "8,432"
        assert format_value("0", 0) == "0"
        assert format_value("100", 0) == "100"

    def test_float(self):
        assert format_value("6.23", 1) == "6.2"
        assert format_value("0.0", 1) == "0.0"
        assert format_value("100.0", 1) == "100.0"

    def test_string(self):
        assert format_value("Good day", 2) == "Good day"
        assert format_value("", 2) == "\u2013"

    def test_duration(self):
        assert format_value("465", 3) == "7h 45m"
        assert format_value("60", 3) == "1h"
        assert format_value("30", 3) == "30m"
        assert format_value("0", 3) == "0m"

    def test_time_from_midnight(self):
        assert format_value("420", 4) == "7:00 AM"
        assert format_value("0", 4) == "12:00 AM"
        assert format_value("720", 4) == "12:00 PM"
        assert format_value("1380", 4) == "11:00 PM"

    def test_percentage(self):
        assert format_value("0.82", 5) == "82%"
        assert format_value("1.0", 5) == "100%"
        assert format_value("0.0", 5) == "0%"

    def test_time_from_midday(self):
        assert format_value("0", 6) == "12:00 PM"
        assert format_value("60", 6) == "1:00 PM"
        assert format_value("-720", 6) == "12:00 AM"

    def test_boolean(self):
        assert format_value("1", 7) == "Yes"
        assert format_value("0", 7) == "No"

    def test_scale(self):
        assert format_value("7", 8) == "7/9"
        assert format_value("1", 8) == "1/9"

    def test_none(self):
        assert format_value(None, 0) == "\u2013"
        assert format_value(None, 2) == "\u2013"
        assert format_value(None, 7) == "\u2013"

    def test_empty_string(self):
        assert format_value("", 0) == "\u2013"
