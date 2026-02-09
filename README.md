# Exist.io/Obsidian Integration
Backup and syncronize your [Exist.io](https://exist.io/) data with Obsidian notebooks and other outputs.

## Components
### exist-backup
Back up your [Exist.io](https://exist.io/) data to a local SQLite database and export it as Obsidian-compatible markdown notes.

### exist-export
coming soon

## Features
- **Incremental sync** — fetches only new data since your last sync, with automatic rate-limit handling and pagination
- **Full sync** — re-downloads your complete history on demand
- **Obsidian export** — renders daily notes from a Jinja2 template, organized by year (`export/2025/2025-01-15.md`)
- **Human-readable formatting** — durations, percentages, booleans, star ratings, and more are formatted for display
- **Per-attribute error isolation** — a single failing attribute won't abort the rest of the sync
- **Docker support** — run as a container with mounted volumes for config, data, and export

## Requirements
- Python 3.12+
- An Exist.io API token (get one from your [Exist.io account settings](https://exist.io/account/apps/))

## Installation
Clone the repo and install with [uv](https://docs.astral.sh/uv/):

```sh
uv sync
```

Or install directly with pip:

```sh
pip install .
```

## Configuration
The app looks for configuration in this order:
1. A path passed with `--config / -c`
2. The `EXIST_BACKUP_CONFIG` environment variable
3. `/config/config.toml` (default, intended for Docker)

Create a `config.toml`:

```toml
[auth]
token = "your_exist_api_token"

[sync]
database = "data/exist.db"

[export]
output_dir = "export"
template = "daily"       # built-in "daily" template, or a path to a custom .j2 file
```

Alternatively, skip the `[auth]` section and set the `EXIST_TOKEN` environment variable instead:

```sh
export EXIST_TOKEN="your_exist_api_token"
```

## Usage
All commands accept an optional `-c /path/to/config.toml` flag. Examples below assume you are using uv:

### Sync data from Exist.io
**Incremental sync** (default) — fetches data from the last sync point through yesterday:

```sh
uv run exist-backup sync
```

**Full sync** — re-downloads all historical data:

```sh
uv run exist-backup sync --full
```

### Export to Obsidian markdown
Export daily notes for a date range:

```sh
uv run exist-backup export --from 2025-01-01 --to 2025-01-31
```

If `--to` is omitted it defaults to today. Files are written to `<output_dir>/<year>/<date>.md`.

### Check sync status
Show the last sync time, attribute count, total values, and date range covered:

```sh
uv run exist-backup status
```

## Docker
Build and run with Docker Compose:

```yaml
# docker-compose.yml
services:
  exist-backup:
    build: .
    volumes:
      - ./config:/config
      - ./data:/data
      - /path/to/obsidian/vault:/export
    environment:
      - EXIST_TOKEN=${EXIST_TOKEN}
```

```sh
# Sync
docker compose run --rm exist-backup sync

# Export
docker compose run --rm exist-backup export --from 2025-01-01

# Status
docker compose run --rm exist-backup status
```

## Development
```sh
uv sync                  # install deps + dev deps
uv run pytest            # run tests
```
