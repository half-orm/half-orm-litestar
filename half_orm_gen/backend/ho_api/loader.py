"""
Load CRUD access configuration from "half_orm_meta.api" tables.

Replaces getattr(mod, 'CRUD_ACCESS', None) in both runtime.py and crud_routes.py.
"""

from .models import HoApiModels


async def load_crud_access(model, schema_name: str, table_name: str) -> dict | None:
    """Reconstruct a CRUD_ACCESS-compatible dict from "half_orm_meta.api" tables.

    Returns None if no routes are defined for this relation.
    """
    api = HoApiModels(model)

    routes = await api.route()(
        schema_name=schema_name, table_name=table_name, deprecated=False
    ).ho_aselect('verb')
    if not routes:
        return None

    crud_access: dict = {}
    for route_row in routes:
        verb = route_row['verb']
        accesses = await api.access()(
            schema_name=schema_name, table_name=table_name, verb=verb
        ).ho_aselect()

        verb_dict: dict = {}
        for acc in accesses:
            role    = acc['role_name']
            acc_id  = acc['id']

            out_rows = await api.field_access_out()(access_id=acc_id).ho_aselect('field_name')
            in_rows  = await api.field_access_in()(access_id=acc_id).ho_aselect('field_name')

            filter_rows = await api.access_filter()(access_id=acc_id).ho_aselect('filter_id')
            filter_names: list[str] = []
            for fr in filter_rows:
                f = await api.filter()(id=fr['filter_id']).ho_aselect('name')
                if f:
                    filter_names.append(f[0]['name'])

            # all_fields_* = TRUE  → None (all fields, CRUD_ACCESS semantics)
            # all_fields_* = FALSE → explicit list (may be empty = no fields)
            out    = None if acc['all_fields_out'] else [r['field_name'] for r in out_rows]
            in_val = None if acc['all_fields_in']  else [r['field_name'] for r in in_rows]

            entry: dict = {}
            if out is not None:
                entry['out'] = out
            if in_val is not None:
                entry['in'] = in_val
            if filter_names:
                entry['filters'] = filter_names
            verb_dict[role] = entry or None

        crud_access[verb] = verb_dict

    return crud_access


_SYSTEM_ROLES = [
    ('anonymous', False),
    ('connected', False),
    ('admin',     False),
]


async def ensure_system_roles(model) -> None:
    """Insert each system role individually if not already present."""
    api = HoApiModels(model)
    Role = api.role()
    for name, deletable in _SYSTEM_ROLES:
        if not await Role(name=name).ho_aselect('name'):
            await Role(name=name, deletable=deletable).ho_ainsert()


async def reconcile_catalog(model) -> None:
    """Sync routes/fields with pg_catalog: insert new, flag deprecated, unflag restored."""
    api  = HoApiModels(model)
    meta = model.ho_meta()

    live_relations = {(v['schema'], v['table']) for v in meta.values()}
    live_fields = {
        (v['schema'], v['table'], f['name'])
        for v in meta.values()
        for f in v.get('fields', [])
    }

    # ── Routes ──────────────────────────────────────────────────────────────
    db_routes = {
        (r['schema_name'], r['table_name'], r['verb']): r['deprecated']
        for r in await api.route()().ho_aselect()
    }
    db_relations = {(s, t) for s, t, _ in db_routes}

    for schema, table in live_relations - db_relations:
        for verb in ('GET', 'POST', 'PUT', 'DELETE'):
            await api.route()(
                schema_name=schema, table_name=table, verb=verb
            ).ho_ainsert()

    for (schema, table, verb), was_deprecated in db_routes.items():
        should = (schema, table) not in live_relations
        if was_deprecated != should:
            await api.route()(
                schema_name=schema, table_name=table, verb=verb
            ).ho_aupdate(deprecated=should)

    # ── Fields ───────────────────────────────────────────────────────────────
    db_fields = {
        (r['schema_name'], r['table_name'], r['column_name']): r['deprecated']
        for r in await api.field()().ho_aselect()
    }

    for (schema, table, col) in live_fields - set(db_fields):
        await api.field()(
            schema_name=schema, table_name=table, column_name=col
        ).ho_ainsert()

    for (schema, table, col), was_deprecated in db_fields.items():
        should = (schema, table, col) not in live_fields
        if was_deprecated != should:
            await api.field()(
                schema_name=schema, table_name=table, column_name=col
            ).ho_aupdate(deprecated=should)
