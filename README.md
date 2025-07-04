# half-orm-test-extension

A simple test extension for the halfORM ecosystem, demonstrating the plugin system and CLI integration.

## Installation

```bash
pip install half-orm-test-extension
```

## Usage

Once installed, the extension automatically integrates with the `half_orm` command:

### Basic Commands

```bash
# Simple greeting
half_orm test-extension greet

# Custom name
half_orm test-extension greet --name "Developer"
```

### Project Status

```bash
# Show current halfORM project info (if in a project directory)
half_orm test-extension status
```

## Purpose

This extension serves as:

1. **Example Implementation**: Shows how to create halfORM extensions
2. **Testing Tool**: Validates the extension discovery and integration system
3. **Development Template**: Provides a starting point for other extensions

## Development

```bash
# Clone and install in development mode
git clone https://github.com/collorg/half-orm-test-extension.git
cd half-orm-test-extension
pip install -e .

# Run tests
pytest tests/

# Verify integration
half_orm --list-extensions
half_orm test-extension greet
```

## Features Demonstrated

- ✅ CLI integration with the `half_orm` command
- ✅ Configuration management
- ✅ halfORM project detection and information display
- ✅ Database introspection (when halfORM_dev available)
- ✅ Extension metadata and documentation
- ✅ Error handling and graceful degradation
- ✅ Unit testing framework

## Architecture

```
half_orm_test_extention/
├── __init__.py              # Package initialization
└── cli_extension.py         # Main CLI integration (required)

tests/
└── test_extension.py       # Unit tests

setup.py                    # Package configuration
README.md                   # This file
```

## Extension Interface

The key integration point is `cli_extension.py`:

```python
def add_commands(main_group):
    # Add commands to the main half_orm CLI
    pass

EXTENSION_INFO = {
    # Extension metadata
}
```

This follows the halfORM ecosystem conventions for automatic discovery and integration.
