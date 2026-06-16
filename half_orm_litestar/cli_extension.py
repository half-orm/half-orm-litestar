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

    @litestar.command('gen-frontend')
    @click.option('--svelte', 'framework', flag_value='svelte', default=True,
                  help='Generate a SvelteKit 5 application (default).')
    @click.option('--output', default=None,
                  help='Output directory (default: frontend/<framework>).')
    def gen_frontend(framework, output):
        """Generate a throwaway SvelteKit POC from CRUD_ACCESS introspection.

        Produces a complete SvelteKit application with Tailwind CSS, Svelte 5
        runes, per-resource list/detail/create pages, and a minimal JWT login.

        Must be run from inside a half-orm-dev project directory.
        """
        try:
            from half_orm_dev.repo import Repo
        except ImportError:
            click.echo(
                'Error: half_orm_dev is not installed. '
                'Install it with: pip install half-orm-dev',
                err=True,
            )
            import sys; sys.exit(1)

        try:
            repo = Repo()
        except Exception as exc:
            click.echo(
                f'Error: could not load the halfORM project ({exc}).\n'
                'Make sure you are inside a half-orm-dev project directory.',
                err=True,
            )
            import sys; sys.exit(1)

        api_version = _read_api_version()
        output_dir = Path(output) if output else Path('frontend') / framework

        if framework == 'svelte':
            from half_orm_litestar.gen_app.svelte import SvelteAppGenerator
            generator = SvelteAppGenerator()
        else:
            click.echo(f'Error: unknown framework "{framework}".', err=True)
            import sys; sys.exit(1)

        from half_orm_litestar.gen_app import GenApp
        click.echo(f'Generating {framework} application → {output_dir}')
        GenApp(repo, generator=generator, output_dir=output_dir, api_version=api_version)

    @litestar.command('gen-store')
    @click.option('--svelte', 'framework', flag_value='svelte', default=True,
                  help='Generate Svelte/TypeScript stores (default).')
    @click.option('--output', default=None,
                  help='Output directory (default: frontend/<framework>).')
    def gen_store(framework, output):
        """Generate frontend stores from CRUD_ACCESS introspection.

        Reads the same CRUD_ACCESS declarations used by `generate` and
        produces one TypeScript file per resource plus an index.ts with
        re-exports and a hoAccess() helper.

        Must be run from inside a half-orm-dev project directory.
        """
        try:
            from half_orm_dev.repo import Repo
        except ImportError:
            click.echo(
                'Error: half_orm_dev is not installed. '
                'Install it with: pip install half-orm-dev',
                err=True,
            )
            import sys; sys.exit(1)

        try:
            repo = Repo()
        except Exception as exc:
            click.echo(
                f'Error: could not load the halfORM project ({exc}).\n'
                'Make sure you are inside a half-orm-dev project directory.',
                err=True,
            )
            import sys; sys.exit(1)

        api_version = _read_api_version()
        output_dir = Path(output) if output else Path('frontend') / framework

        if framework == 'svelte':
            from half_orm_litestar.gen_store.svelte import SvelteGenerator
            generator = SvelteGenerator()
        else:
            click.echo(f'Error: unknown framework "{framework}".', err=True)
            import sys; sys.exit(1)

        from half_orm_litestar.gen_store import GenStore
        click.echo(f'Generating {framework} stores → {output_dir}')
        GenStore(repo, generator=generator, output_dir=output_dir, api_version=api_version)

    @litestar.command(
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    )
    @click.argument('args', nargs=-1, type=click.UNPROCESSED)
    def run(args):
        """Run the Litestar app (proxy to `litestar run`).

        All options are forwarded to `litestar run`, e.g.:

            half_orm litestar run --reload --debug --port 8080
        """
        import subprocess
        cmd = ['litestar', '--app', 'api.app:application', 'run'] + list(args)
        sys.exit(subprocess.call(cmd))