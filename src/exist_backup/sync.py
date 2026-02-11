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

    if full:
        # Full sync: fetch each attribute's complete history individually
        print("Fetching attributes...", file=sys.stderr)
        attributes = client.get_attributes()
        for attr in attributes:
            db.upsert_attribute(conn, attr)
        print(f"  {len(attributes)} attributes synced", file=sys.stderr)

        for attr in attributes:
            attr_name = attr["name"]
            try:
                print(f"  Syncing {attr_name}...", file=sys.stderr, end="")

                values = list(client.get_attribute_values(
                    attr_name,
                    date_max=str(yesterday),
                ))

                count = db.upsert_values(conn, attr_name, values)
                values_synced += count
                attributes_synced += 1
                print(f" {count} values", file=sys.stderr)

            except Exception as e:
                errors.append(f"{attr_name}: {e}")
                print(f" ERROR: {e}", file=sys.stderr)
    else:
        # Incremental sync: bulk fetch via /attributes/with-values/
        oldest = db.get_oldest_last_sync_date(conn)

        if oldest and oldest >= str(yesterday):
            print("All attributes up to date, nothing to sync.", file=sys.stderr)
        else:
            if oldest:
                oldest_date = date.fromisoformat(oldest)
                days_needed = max(1, min(31, (yesterday - oldest_date).days))
            else:
                days_needed = 31

            print(f"Fetching attributes with values (last {days_needed} days)...", file=sys.stderr)

            try:
                for attr in client.get_attributes_with_values(
                    days=days_needed,
                    date_max=str(yesterday),
                ):
                    attr_name = attr["name"]
                    try:
                        db.upsert_attribute(conn, attr)
                        attr_values = attr.get("values", [])

                        last_date = db.get_last_sync_date(conn, attr_name)
                        if last_date:
                            attr_values = [v for v in attr_values if v["date"] > last_date]

                        if attr_values:
                            count = db.upsert_values(conn, attr_name, attr_values)
                            values_synced += count
                            attributes_synced += 1
                            print(f"  {attr_name}: {count} values", file=sys.stderr)

                    except Exception as e:
                        errors.append(f"{attr_name}: {e}")
                        print(f"  {attr_name}: ERROR: {e}", file=sys.stderr)
            except Exception as e:
                errors.append(f"Bulk fetch: {e}")
                print(f"  Bulk fetch error: {e}", file=sys.stderr)

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
