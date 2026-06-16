"""
Abstract base class for frontend store generators.
"""

from abc import ABC, abstractmethod
from pathlib import Path


class StoreGenerator(ABC):

    PY_TO_TS = {
        'str':               'string',
        'int':               'number',
        'float':             'number',
        'bool':              'boolean',
        'uuid.UUID':         'string',
        'datetime.datetime': 'string',
        'datetime.date':     'string',
        'datetime.time':     'string',
        'datetime.timedelta':'string',
        'decimal.Decimal':   'number',
    }

    def ts_type(self, py_type_str: str) -> str:
        return self.PY_TO_TS.get(py_type_str, 'unknown')

    def resource_name(self, schema: str, table: str) -> str:
        """blogAuthor (camelCase)"""
        parts = schema.split('_') + table.split('_')
        return parts[0].lower() + ''.join(p.capitalize() for p in parts[1:])

    def interface_name(self, schema: str, table: str) -> str:
        """BlogAuthor (PascalCase)"""
        parts = schema.split('_') + table.split('_')
        return ''.join(p.capitalize() for p in parts)

    @abstractmethod
    def generate(self, classes, api_version, output_dir: Path) -> None: ...