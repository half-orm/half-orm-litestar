"""
Auto-CRUD route generation from CRUD_ACCESS + halfORM introspection.

For each relation module that defines CRUD_ACCESS, generates Litestar
route handlers for the verbs declared, skipping any verb already covered
by an @api_* decorated method.
"""

import importlib
from typing import Iterable, Tuple, Type

from half_orm.relation import Relation

from half_orm_litestar import templates as T
from half_orm_litestar.api_routes import _annotation_str


_LITESTAR_PATH_TYPE_MAP = {
    'uuid.UUID':          'uuid',
    'int':                'int',
    'str':                'str',
    'float':              'float',
    'decimal.Decimal':    'decimal',
    'datetime.date':      'date',
    'datetime.datetime':  'datetime',
    'datetime.time':      'time',
    'datetime.timedelta': 'timedelta',
}


def _py_type_str(py_type) -> str:
    """Return the fully-qualified Python type string for an annotation."""
    return _annotation_str(py_type)


def _path_type_str(py_type) -> str:
    """Return the Litestar path-param keyword for a Python type."""
    return _LITESTAR_PATH_TYPE_MAP.get(_py_type_str(py_type), 'str')


def _instance(relation):
    """Return a bare instance of the relation (no DB query)."""
    return relation()


def _simple_pk(relation) -> Tuple[str, str, str] | None:
    """Return (pk_field_name, litestar_path_type, py_type_str) for single-column PKs.

    Returns None for composite or absent PKs.
    _ho_pkey is an instance attribute, so we must instantiate the relation.
    """
    pkey = getattr(_instance(relation), '_ho_pkey', {})
    if len(pkey) != 1:
        return None
    field_name, field_obj = next(iter(pkey.items()))
    return field_name, _path_type_str(field_obj.py_type), _py_type_str(field_obj.py_type)


def _filter_params_str(relation) -> Tuple[str, str]:
    """Return (filter_params_block, filter_dict_str) for query-param filters.

    _ho_fields is an instance attribute, so we must instantiate the relation.
    """
    fields = getattr(_instance(relation), '_ho_fields', {})
    lines = []
    dict_items = []
    for fname, fobj in fields.items():
        type_str = _py_type_str(fobj.py_type)
        lines.append(f'    {fname}: Optional[{type_str}] = None,\n')
        dict_items.append(f"'{fname}': {fname}")
    filter_params = ''.join(lines)
    filter_dict = ', '.join(dict_items)
    return filter_params, filter_dict


def _typedict_name(relation) -> str:
    """Return the ho_typeddicts class name for a relation."""
    schema_cap = ''.join(p.capitalize() for p in relation._schemaname.split('_'))
    table_cap = relation.__name__
    return f'{schema_cap}{table_cap}Dict'


def _validate_crud_access(crud_access: dict, module_str: str) -> None:
    """Warn about known misconfiguration patterns in CRUD_ACCESS."""
    valid_verbs = {'GET', 'POST', 'PUT', 'PATCH', 'DELETE'}
    for verb in crud_access:
        if verb not in valid_verbs:
            print(f'  WARNING {module_str}.CRUD_ACCESS: unknown verb "{verb}"')


def generate_crud_routes(
    classes: Iterable[Tuple[Type[Relation], str]],
    api_version,
    covered: set,
) -> Tuple[list, list]:
    """Generate auto-CRUD blocks for all relations that define CRUD_ACCESS.

    Skips verbs already covered by @api_* (present in *covered* set).

    Returns (blocks, route_handler_names).
    """
    blocks: list[str] = []
    route_handlers: list[str] = []

    version_prefix = f'/v{api_version}' if api_version is not None else ''

    for relation, _relation_type in classes:
        module_str   = relation.__module__
        schema       = '.'.join(module_str.split('.')[:-1])
        module_name  = module_str.split('.')[-1]
        module_alias = module_str.replace('.', '_')

        try:
            mod = importlib.import_module(module_str)
        except ImportError as exc:
            print(f'  WARNING: cannot import {module_str}: {exc}')
            continue

        crud_access = getattr(mod, 'CRUD_ACCESS', None)
        if not crud_access:
            continue

        _validate_crud_access(crud_access, module_str)

        kind = getattr(relation, '_ho_kind', 'Table')
        is_table = kind == 'Table'
        schema_name = relation._schemaname.replace('.', '_')
        table_name = relation.__name__.lower()
        base_path = f'{version_prefix}/{schema_name}/{table_name}'
        handler_prefix = f'_crud_{module_alias}'
        td_name = _typedict_name(relation)
        pk_info = _simple_pk(relation)

        blocks.append(T.CRUD_MODULE_IMPORT.format(
            schema=schema,
            module_name=module_name,
            module_alias=module_alias,
        ))

        filter_params, filter_dict = _filter_params_str(relation)

        # GET list — always generated (tables and views)
        if (module_str, 'GET') not in covered and 'GET' in crud_access:
            handler_name = f'{handler_prefix}_list'
            blocks.append(T.CRUD_GET_LIST.format(
                path=base_path,
                handler_name=handler_name,
                filter_params=filter_params,
                filter_dict=filter_dict,
                module_alias=module_alias,
                class_name=relation.__name__,
                typedict_name=td_name,
            ))
            route_handlers.append(handler_name)

        # GET /{pk} — only if single PK
        if pk_info and (module_str, 'GET') not in covered and 'GET' in crud_access:
            pk_field, pk_path_type, pk_py_type = pk_info
            handler_name = f'{handler_prefix}_get'
            blocks.append(T.CRUD_GET_ONE.format(
                path=base_path,
                handler_name=handler_prefix,
                pk_field=pk_field,
                pk_path_type=pk_path_type,
                pk_py_type=pk_py_type,
                module_alias=module_alias,
                class_name=relation.__name__,
                typedict_name=td_name,
            ))
            route_handlers.append(handler_name)

        # Write verbs — tables only
        if is_table and pk_info:
            pk_field, pk_path_type, pk_py_type = pk_info

            if (module_str, 'POST') not in covered and 'POST' in crud_access:
                handler_name = f'{handler_prefix}_create'
                blocks.append(T.CRUD_POST.format(
                    path=base_path,
                    handler_name=handler_prefix,
                    module_alias=module_alias,
                    class_name=relation.__name__,
                    typedict_name=td_name,
                ))
                route_handlers.append(handler_name)

            if (module_str, 'PUT') not in covered and 'PUT' in crud_access:
                handler_name = f'{handler_prefix}_update'
                blocks.append(T.CRUD_PUT.format(
                    path=base_path,
                    handler_name=handler_prefix,
                    pk_field=pk_field,
                    pk_path_type=pk_path_type,
                    pk_py_type=pk_py_type,
                    module_alias=module_alias,
                    class_name=relation.__name__,
                    typedict_name=td_name,
                ))
                route_handlers.append(handler_name)

            if (module_str, 'DELETE') not in covered and 'DELETE' in crud_access:
                handler_name = f'{handler_prefix}_delete'
                blocks.append(T.CRUD_DELETE.format(
                    path=base_path,
                    handler_name=handler_prefix,
                    pk_field=pk_field,
                    pk_path_type=pk_path_type,
                    pk_py_type=pk_py_type,
                    module_alias=module_alias,
                    class_name=relation.__name__,
                    typedict_name=td_name,
                ))
                route_handlers.append(handler_name)

    return blocks, route_handlers
