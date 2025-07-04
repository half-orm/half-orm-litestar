"""
Tests for half-orm-test-extension extension
"""

import pytest
from click.testing import CliRunner
import click

# Import our extension
from cli_extension import add_commands, EXTENSION_INFO


class TestExtension:
    
    def setup_method(self):
        """Setup for each test"""
        self.runner = CliRunner()
        
        # Create a temporary CLI group for testing
        @click.group()
        def test_cli():
            pass
        
        # Add our extension commands
        add_commands(test_cli)
        self.cli = test_cli
    
    def test_extension_info(self):
        """Test extension metadata"""
        assert EXTENSION_INFO['version'] == '0.1.0'
        assert 'test extension' in EXTENSION_INFO['description']
    
    def test_greet_default(self):
        """Test default greet command"""
        result = self.runner.invoke(self.cli, ['test-extension', 'greet'])
        assert result.exit_code == 0
        assert 'Hello, halfORM!' in result.output
    
    def test_greet_with_name(self):
        """Test greet with custom name"""
        result = self.runner.invoke(self.cli, ['test-extension', 'greet', '--name', 'World'])
        assert result.exit_code == 0
        assert 'Hello, World!' in result.output
    
    def test_status_command(self):
        """Test status command"""            
        result = self.runner.invoke(self.cli, ['test-extension', 'status'])
        assert result.exit_code == 0
        assert 'Test Extension Status' in result.output
        assert '0.1.0' in result.output


if __name__ == '__main__':
    pytest.main([__file__, '-v'])