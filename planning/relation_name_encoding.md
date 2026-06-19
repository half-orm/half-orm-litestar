# Relation name encoding

## Problem

PostgreSQL allows arbitrary identifiers for schema and table names:

```sql
CREATE SCHEMA "mon schéma";
CREATE TABLE "mon schéma"."ma très belle table!" (...);
```

`relation._t_fqrn` gives the raw names as stored in the catalog:
`('db', 'mon schéma', 'ma très belle table!')`.

Using these raw names directly breaks:

1. **URL paths** — `/v0/mon schéma/ma très belle table!` is invalid
2. **TypeScript/Python identifiers** — `mon schémaState`, `Ma très belle table!Out`
3. **File names** — `mon schéma_ma très belle table!.svelte.ts`

## Two distinct transformations needed

| Use | Transform | Example |
|-----|-----------|---------|
| URL path segments | `urllib.parse.quote(name, safe='')` | `mon%20sch%C3%A9ma` |
| Identifiers & file names | unicode slug (spaces/special chars → `_`, accents normalised) | `mon_schema` |

The two forms must stay in sync: the generated store uses the URL form for
`_BASE` and the slug form for TypeScript class/variable names.

## Where to implement

In **half-orm** (or a shared utility in half-orm-dev), so all consumers
(half-orm-litestar, future generators) share the same canonical encoding.

Proposed API:

```python
relation.url_path()    # → 'mon%20sch%C3%A9ma/ma%20tr%C3%A8s%20belle%20table%21'
relation.slug()        # → 'mon_schema/ma_tres_belle_table'
```

Or as standalone helpers operating on `_t_fqrn`:

```python
from half_orm.utils import url_segment, identifier_slug

url_segment('mon schéma')      # → 'mon%20sch%C3%A9ma'
identifier_slug('mon schéma')  # → 'mon_schema'
```

## Current workaround

Simple names (`api`, `role_has_route`) work as-is with `_t_fqrn[1]` and
`_t_fqrn[2]`. The encoding problem only manifests with quoted identifiers
containing spaces or non-ASCII characters.
