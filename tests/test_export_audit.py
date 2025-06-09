#!/usr/bin/env python3
import click
import sys
from typing import Optional

from ci_log_analysis.cli.commands import analyze, export, configure
from ci_log_analysis.config import SystemConfig


@click.group()
@click.version_option()
@click.option("--config", "-c", default="./config.yaml", help="Path to config file")
@click.pass_context
def cli(ctx: click.Context, config: str) -> None:
    """CI Log Analysis System - identify root causes in CI logs."""
    try:
        ctx.ensure_object(dict)
        ctx.obj["config"] = SystemConfig.from_yaml(config)
    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        sys.exit(1)


# Add subcommands
cli.add_command(analyze.command)
cli.add_command(export.command)
cli.add_command(configure.command)


def main() -> Optional[int]:
    """Entry point for the CI Log Analysis CLI."""
    try:
        return cli(standalone_mode=False)
    except click.exceptions.Abort:
        click.echo("Operation aborted.", err=True)
        return 1
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())