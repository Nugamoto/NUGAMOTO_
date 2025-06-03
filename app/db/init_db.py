from __future__ import annotations

"""
Database initialisation utility.

Usage (CLI):
    python -m app.db.init_db          # create tables if they don't exist
    python -m app.db.init_db --reset  # drop all tables first, then recreate

The module can also be imported and `init_db()` called programmatically.
"""

import click
from sqlalchemy import MetaData

from app.db.session import engine
from app.db.base import Base  # Base must already have all models imported!
from app.models import user  # noqa: F401  – ensures User model is registered
from app.models import kitchen  # noqa: F401  – ensures Kitchen model is registered

def init_db(*, reset: bool = False) -> None:
    """
    Create all database tables (optionally dropping existing ones first).

    Args:
        reset: If True, **drops** all tables before creating them again.
    """
    metadata: MetaData = Base.metadata

    if reset:
        click.echo("Dropping existing tables …")
        metadata.drop_all(bind=engine)

    click.echo("Creating tables …")
    metadata.create_all(bind=engine)
    click.echo("Done ✔")


# ------------------------------------------------------------------------- #
# Optional command-line interface using `click`                             #
# ------------------------------------------------------------------------- #
@click.command(help="Initialise the database schema.")
@click.option(
    "--reset",
    is_flag=True,
    default=False,
    help="Drop all tables before recreating them.",
)
def _cli(reset: bool) -> None:  # pragma: no cover
    """CLI wrapper."""
    init_db(reset=reset)


if __name__ == "__main__":  # pragma: no cover
    _cli()
