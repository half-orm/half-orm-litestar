"""
CLI extension for half-orm-litestar.

Registers the ``litestar`` sub-command group under the ``half_orm`` CLI::

    half_orm litestar generate
"""

import sys
import click
from half_orm.cli_utils import create_and_register_extension


def add_commands(main_group):
    """Required entry point for halfORM extensions."""

    @create_and_register_extension(main_group, sys.modules[__name__])
    def litestar():
        """Generate and manage a Litestar API from a halfORM project."""
        pass

    @litestar.command()
    @click.option(
        '--dry-run', is_flag=True, default=False,
        help='Print what would be generated without writing any file.',
    )
    def generate(dry_run):
        """Generate api/main.py from @api_* decorated halfORM methods.

        Must be run from inside a half-orm-dev project directory.
        On first run, missing scaffolding files (guards.py, custom/) are
        created automatically and are never overwritten on subsequent runs.
        """
        try:
            from half_orm_dev.repo import Repo
        except ImportError:
            click.echo(
                'Error: half_orm_dev is not installed. '
                'Install it with: pip install half-orm-dev',
                err=True,
            )
            sys.exit(1)

        try:
            repo = Repo()
        except Exception as exc:
            click.echo(
                f'Error: could not load the halfORM project ({exc}).\n'
                'Make sure you are inside a half-orm-dev project directory.',
                err=True,
            )
            sys.exit(1)

        if dry_run:
            click.echo('[dry-run] would generate api/main.py for project: ' + repo.name)
            return

        from half_orm_litestar.generate import GenApi
        click.echo(f'Generating Litestar API for project: {repo.name}')
        GenApi(repo)