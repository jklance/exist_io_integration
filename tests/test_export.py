"""Tests for Obsidian markdown export."""

from datetime import date
from pathlib import Path

import pytest

from exist_backup import db
from exist_backup.export import export_date_range, query_day


class TestQueryDay:
    def test_returns_grouped_data(self, populated_db):
        result = query_day(populated_db, "2024-12-01")

        assert result["date"] == "2024-12-01"
        assert "Activity" in result["groups"]
        assert "Sleep" in result["groups"]

        # Check an activity entry
        activity_attrs = result["groups"]["Activity"]
        steps = next(a for a in activity_attrs if a["name"] == "steps")
        assert steps["formatted_value"] == "8,432"
        assert steps["raw_value"] == "8432"

    def test_collects_boolean_tags(self, populated_db):
        result = query_day(populated_db, "2024-12-01")
        assert "Meditated" in result["tags"]

    def test_no_tag_when_boolean_false(self, populated_db):
        result = query_day(populated_db, "2024-12-02")
        assert "Meditated" not in result["tags"]

    def test_empty_day(self, populated_db):
        result = query_day(populated_db, "2099-01-01")
        assert result["groups"] == {}


class TestExportDateRange:
    def test_writes_markdown_files(self, populated_db, tmp_path):
        config = {
            "sync": {"database": ":memory:"},
            "export": {"output_dir": str(tmp_path / "export"), "template": "daily"},
        }

        # We need to pass a real db path, so write a temp one
        db_path = str(tmp_path / "test.db")
        conn = db.connect(db_path)
        db.init_db(conn)

        # Copy data from populated_db
        profile = db.get_profile(populated_db)
        db.upsert_profile(conn, profile)
        for attr in db.get_all_attributes(populated_db):
            conn.execute(
                """INSERT OR REPLACE INTO attributes
                (name, label, group_name, group_label, group_priority, priority,
                 value_type, value_type_description, service_name, service_label,
                 manual, active, template, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                tuple(attr),
            )
        for val in db.get_values_for_date_range(populated_db, "2024-12-01", "2024-12-03"):
            conn.execute(
                "INSERT OR REPLACE INTO attribute_values (attribute_name, date, value) VALUES (?, ?, ?)",
                (val["attribute_name"], val["date"], val["value"]),
            )
        conn.commit()
        conn.close()

        config["sync"]["database"] = db_path
        count = export_date_range(config, date(2024, 12, 1), date(2024, 12, 3))

        assert count == 3
        md_file = tmp_path / "export" / "2024" / "2024-12-01.md"
        assert md_file.exists()

        content = md_file.read_text()
        assert "Exist.io 2024-12-01" in content
        assert "Steps" in content
        assert "8,432" in content
