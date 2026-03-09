"""CLI application entrypoint.

This module defines the Click command group and registers command
implementations from ``pyskills.cli.commands``.
"""

from __future__ import annotations

import click

from .commands import (
    add,
    adopt,
    check,
    find,
    list_command,
    lock_doctor,
    remove,
    update,
)


@click.group(help="Manage agent skills.")
def cli() -> None:
    """Run the root CLI command group.

    Returns
    -------
    None
        Click handles command execution and process flow.
    """


cli.add_command(add)
cli.add_command(adopt)
cli.add_command(list_command)
cli.add_command(remove)
cli.add_command(find)
cli.add_command(check)
cli.add_command(update)
cli.add_command(lock_doctor)
