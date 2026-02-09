"""Obsidian markdown export from SQLite database."""

import os
from collections import OrderedDict
from datetime import date, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import db, formatting

# Directory containing built-in templates
TEMPLATES_DIR = Path(__file__).parent / "templates"


def query_day(conn, date_str):
    """Query all data for a single day, grouped for template rendering.

    Returns dict with keys: date, groups (OrderedDict of group_label -> list of attr dicts).
    """
    attributes = db.get_all_attributes(conn)
    day_values = {row["attribute_name"]: row["value"] for row in db.get_values_for_date(conn, date_str)}
    profile = db.get_profile(conn)

    groups = OrderedDict()
    tags = []

    for attr in attributes:
        attr_name = attr["name"]
        raw_value = day_values.get(attr_name)

        # Skip attributes with no data for this day
        if raw_value is None and attr_name not in day_values:
            continue

        group_label = attr["group_label"]
        if group_label not in groups:
            groups[group_label] = []

        value_type = attr["value_type"]
        formatted = formatting.format_value(raw_value, value_type, profile)

        entry = {
            "name": attr_name,
            "label": attr["label"],
            "value_type": value_type,
            "raw_value": raw_value,
            "formatted_value": formatted,
        }
        groups[group_label].append(entry)

        # Collect boolean tags where value=1
        if value_type == 7 and raw_value is not None and int(float(raw_value)) == 1:
            tags.append(attr["label"])

    return {
        "date": date_str,
        "groups": groups,
        "tags": tags,
    }


def get_jinja_env(template_name_or_path):
    """Create Jinja2 environment, searching built-in templates and custom paths."""
    search_paths = [str(TEMPLATES_DIR)]

    # If it's a path to a custom template, add its directory
    custom_path = Path(template_name_or_path)
    if custom_path.suffix == ".j2" and custom_path.parent.exists():
        search_paths.insert(0, str(custom_path.parent))

    return Environment(
        loader=FileSystemLoader(search_paths),
        autoescape=select_autoescape([]),
        keep_trailing_newline=True,
    )


def resolve_template_name(template_setting):
    """Resolve the template config value to a filename."""
    if template_setting in ("daily", "weekly"):
        return f"{template_setting}.md.j2"
    # Assume it's a path to a custom template
    return Path(template_setting).name


def export_date_range(config, date_from, date_to):
    """Export Obsidian markdown files for a date range.

    Args:
        config: Parsed configuration dict.
        date_from: Start date (inclusive) as date object.
        date_to: End date (inclusive) as date object.

    Returns:
        Number of files written.
    """
    conn = db.connect(config["sync"]["database"])
    output_dir = Path(config["export"]["output_dir"])
    template_setting = config["export"].get("template", "daily")

    env = get_jinja_env(template_setting)
    template_name = resolve_template_name(template_setting)
    template = env.get_template(template_name)

    files_written = 0
    current = date_from

    while current <= date_to:
        date_str = current.isoformat()
        day_data = query_day(conn, date_str)

        # Only write if there's data for this day
        if day_data["groups"]:
            year_dir = output_dir / str(current.year)
            year_dir.mkdir(parents=True, exist_ok=True)
            out_path = year_dir / f"{date_str}.md"

            content = template.render(**day_data)
            out_path.write_text(content)
            files_written += 1

        current += timedelta(days=1)

    conn.close()
    return files_written
