# half-orm-test-extension - Test Extension
# Complete mini extension for testing the halfORM ecosystem

# =============================================================================
# setup.py
# =============================================================================
from setuptools import setup, find_packages

setup(
    name='half-orm-test-extension',
    version='0.16.0',
    description='test-extension World test extension for halfORM ecosystem',
    long_description="""
# half-orm-test-extension

A simple test extension demonstrating the halfORM ecosystem integration.

## Installation

```bash
pip install half-orm-test-extension
```

## Usage

```bash
half_orm test-extension greet --name "World"
half_orm test-extension status
half_orm test-extension config --set greeting "Bonjour"
```

This extension provides basic commands to test the halfORM CLI integration system.
    """,
    long_description_content_type='text/markdown',
    author='halfORM Team',
    author_email='contact@collorg.org',
    url='https://github.com/collorg/half-orm-test-extension',
    license='GPL-3.0',
    packages=find_packages(),
    install_requires=[
        'half-orm>=0.16.0',
    ],
    extras_require={
        'dev': ['pytest', 'black', 'flake8'],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Database',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    python_requires='>=3.8',
)

