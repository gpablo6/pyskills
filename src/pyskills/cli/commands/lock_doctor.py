"""Implementation for the ``lock-doctor`` command."""

from __future__ import annotations

import click

from pyskills.services.lock_health import diagnose_locks


@click.command(name="lock-doctor")
def lock_doctor() -> None:
    """Inspect local and global lock health."""

    report = diagnose_locks()

    click.echo("Lock doctor")
    click.echo("")

    _print_lock("Global", report.global_lock)
    click.echo("")
    _print_lock("Local", report.local_lock)
    click.echo("")

    if report.warning_count == 0:
        click.echo("No lock health warnings.")
    else:
        click.echo(f"Warnings: {report.warning_count}")


def _print_lock(label: str, health) -> None:  # noqa: ANN001
    """Print one lock health section."""

    click.echo(f"{label} lock")
    click.echo(f"  Path: {health.path}")
    click.echo(f"  Exists: {'yes' if health.exists else 'no'}")
    version = str(health.version) if health.version is not None else "n/a"
    click.echo(f"  Version: {version}")
    click.echo(f"  Entries: {health.entries}")
    for warning in health.warnings:
        click.echo(f"  Warning: {warning}")
