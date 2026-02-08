"""Click CLI: sync, export, and status subcommands."""

from datetime import date

import click

from . import config as config_module
from . import db, sync as sync_module
from .export import export_date_range


@click.group()
@click.option("--config", "-c", "config_path", default=None, help="Path to config.toml")
@click.pass_context
def cli(ctx, config_path):
    """Exist.io backup and Obsidian export tool."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = config_module.load_config(config_path)


@cli.command()
@click.option("--full", is_flag=True, help="Force full historical sync")
@click.pass_context
def sync(ctx, full):
    """Sync data from Exist.io API to local database."""
    result = sync_module.run_sync(ctx.obj["config"], full=full)
    if result["status"] == "error":
        raise SystemExit(1)


@cli.command()
@click.option("--from", "date_from", type=click.DateTime(formats=["%Y-%m-%d"]), required=True,
              help="Start date (YYYY-MM-DD)")
@click.option("--to", "date_to", type=click.DateTime(formats=["%Y-%m-%d"]), default=None,
              help="End date (YYYY-MM-DD), defaults to today")
@click.pass_context
def export(ctx, date_from, date_to):
    """Export data as Obsidian markdown files."""
    if date_to is None:
        date_to = date.today()
    else:
        date_to = date_to.date()

    date_from = date_from.date()
    count = export_date_range(ctx.obj["config"], date_from, date_to)
    click.echo(f"Exported {count} daily notes.")


@cli.command()
@click.pass_context
def status(ctx):
    """Show last sync time, total attributes, total values, date range covered."""
    config = ctx.obj["config"]
    conn = db.connect(config["sync"]["database"])
    db.init_db(conn)
    stats = db.get_sync_status(conn)
    conn.close()

    click.echo(f"Last sync:        {stats['last_sync'] or 'never'}")
    click.echo(f"Attributes:       {stats['total_attributes']}")
    click.echo(f"Total values:     {stats['total_values']}")
    if stats["date_min"]:
        click.echo(f"Date range:       {stats['date_min']} to {stats['date_max']}")
    else:
        click.echo("Date range:       (no data)")
