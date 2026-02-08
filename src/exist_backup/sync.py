"""Sync orchestration — fetch data from Exist.io and store in SQLite."""

import sys
from datetime import date, timedelta

from . import api, db


def run_sync(config, full=False):
    """Run a sync from Exist.io API to local SQLite database.

    Args:
        config: Parsed configuration dict.
        full: If True, fetch all historical data. Otherwise incremental.

    Returns:
        dict with keys: attributes_synced, values_synced, status, errors
    """
    token = config["auth"]["token"]
    if not token:
        raise SystemExit("No API token configured. Set EXIST_TOKEN or auth.token in config.toml.")

    client = api.ExistClient(token)
    conn = db.connect(config["sync"]["database"])
    db.init_db(conn)

    yesterday = date.today() - timedelta(days=1)
    sync_type = "full" if full else "incremental"
    attributes_synced = 0
    values_synced = 0
    errors = []

    # 1. Fetch + upsert user profile
    print("Fetching user profile...", file=sys.stderr)
    profile = client.get_profile()
    db.upsert_profile(conn, profile)

    # 2. Fetch all attributes (paginated) → upsert metadata
    print("Fetching attributes...", file=sys.stderr)
    attributes = client.get_attributes()
    for attr in attributes:
        db.upsert_attribute(conn, attr)
    print(f"  {len(attributes)} attributes synced", file=sys.stderr)

    # 3. For each attribute, sync values
    for attr in attributes:
        attr_name = attr["name"]
        try:
            last_date = db.get_last_sync_date(conn, attr_name)

            if not full and last_date and last_date >= str(yesterday):
                # Up to date, skip
                continue

            print(f"  Syncing {attr_name}...", file=sys.stderr, end="")

            values = list(client.get_attribute_values(
                attr_name,
                date_max=str(yesterday),
            ))

            if not full and last_date:
                # Incremental: only keep values newer than what we have
                values = [v for v in values if v["date"] > last_date]

            count = db.upsert_values(conn, attr_name, values)
            values_synced += count
            attributes_synced += 1
            print(f" {count} values", file=sys.stderr)

        except Exception as e:
            errors.append(f"{attr_name}: {e}")
            print(f" ERROR: {e}", file=sys.stderr)

    # 4. Write sync_log entry
    status = "success" if not errors else "partial" if attributes_synced > 0 else "error"
    error_msg = "\n".join(errors) if errors else None
    db.write_sync_log(conn, sync_type, attributes_synced, values_synced, status, error_msg)

    conn.close()

    result = {
        "attributes_synced": attributes_synced,
        "values_synced": values_synced,
        "status": status,
        "errors": errors,
    }

    print(f"\nSync complete: {attributes_synced} attributes, {values_synced} values ({status})", file=sys.stderr)
    if errors:
        print(f"  {len(errors)} errors:", file=sys.stderr)
        for e in errors:
            print(f"    {e}", file=sys.stderr)

    return result
