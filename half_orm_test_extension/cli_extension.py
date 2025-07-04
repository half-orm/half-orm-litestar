"""
CLI extension integration for half-orm-test-extension

This module provides the entry point for the halfORM ecosystem plugin system.
"""

import sys
import click
from half_orm.cli_utils import create_and_register_extension


def add_commands(main_group):
    """
    Required entry point for halfORM extensions.
    
    Args:
        main_group: The main Click group for the half_orm command
    """
    
    @create_and_register_extension(main_group, sys.modules[__name__])
    def extension_commands():
        """Simple test extension for halfORM ecosystem"""
        pass
    
    @extension_commands.command()
    @click.option('--name', default='halfORM', help='Name to greet')
    def greet(name):
        """Greet someone with a simple message"""
        click.echo(f"Hello, {name}!")
    
    @extension_commands.command()
    def status():
        """Show extension status"""
        # Get metadata automatically
        from half_orm.cli_utils import get_package_metadata, get_extension_commands
        
        metadata = get_package_metadata(sys.modules[__name__])
        commands = get_extension_commands(extension_commands)
        
        click.echo("🔍 halfORM Test Extension Status")
        click.echo("=" * 35)
        click.echo(f"Version: {metadata['version']}")
        click.echo(f"Author: {metadata['author']}")
        click.echo(f"Description: {metadata['description']}")
        click.echo(f"Commands: {', '.join(commands)}")