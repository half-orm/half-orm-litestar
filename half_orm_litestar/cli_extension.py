"""
CLI extension for half-orm-litestar.

Registers the ``litestar`` sub-command group under the ``half_orm`` CLI::

    half_orm litestar generate
"""

import sys
from pathlib import Path
import click
from half_orm.cli_utils import create_and_register_extension

_VERSION_FILE = Path('api') / '.api_version'


def _read_api_version() -> int:
    try:
        return int(_VERSION_FILE.read_text().strip())
    except (FileNotFoundError, ValueError):
        return 0


def _write_api_version(version: int) -> None:
    _VERSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    _VERSION_FILE.write_text(str(version) + '\n')


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
    @click.option(
        '--bump', is_flag=True, default=False,
        help='Bump the API version to N+1 (asks for confirmation).',
    )
    def generate(dry_run, bump):
        """Generate api/app.py from @api_* decorated halfORM methods.

        The API version is read from api/.api_version (default: 0).
        Use --bump to move to N+1; the new value is saved for future runs.
        To revert a mistaken bump: git checkout api/.api_version.

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

        api_version = _read_api_version()

        if bump:
            next_version = api_version + 1
            click.confirm(
                f'Bump API version from v{api_version} to v{next_version}?',
                abort=True,
            )
            _write_api_version(next_version)
            api_version = next_version

        if dry_run:
            click.echo(
                f'[dry-run] would generate api/app.py for project: {repo.name}'
                f' (v{api_version})'
            )
            return

        from half_orm_litestar.generate import GenApi
        click.echo(f'Generating Litestar API for project: {repo.name} (v{api_version})')
        GenApi(repo, api_version=api_version)

    @litestar.command()
    @click.option('--reload', is_flag=True, default=False, help='Enable auto-reload on file changes.')
    @click.option('--debug', is_flag=True, default=False, help='Enable Litestar debug mode.')
    def run(reload, debug):
        """Run the Litestar app from api/app.py (development helper)."""
        import subprocess
        cmd = ['litestar', '--app', 'api.app:application', 'run']
        if reload:
            cmd.append('--reload')
        if debug:
            cmd.append('--debug')
        sys.exit(subprocess.call(cmd))