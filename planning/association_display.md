# Association display in detail pages

## Concept

An association is a relation that links multiple relations via FK columns:

- Binary:  `A <- AB -> B`
- Ternary: `A <- ABC -> B`
                          `-> C`

## Current behaviour

When viewing a record of `A`, the "Related" section shows raw rows of `AB`
(the junction table), e.g. `project_id | user_id`. This is low-value.

## Desired behaviour

When viewing `A`, show the *associated entities* (`B`, or `(B, C)`) enriched
with the non-FK columns of `AB` (the attributes of the association).

Example — `anonymous.project` → `anonymous.projecthasuser` → `anonymous.user`:

| name (user) | email (user) | role (AB) | joined_at (AB) |
|---|---|---|---|
| Alice | alice@… | admin | 2024-01 |

For a ternary `ABC`, show `(B, C)` on a single row with the extra columns.

## Detection heuristic

A table is an association if all (or nearly all) of its non-PK columns are
simple (single-column) FK fields. The "payload" columns are the non-FK,
non-PK fields.

## Open questions

1. Should the raw `AB` list be hidden entirely, or kept alongside the
   resolved view?
2. Resolution strategy: lookup in existing store (local cache) or dedicated
   API call?
3. Ternary case: many columns on one row — prefer a flat table or a nested
   card per row?

## Where to implement

Possibly at the `half-orm` or `half-orm-dev` level rather than in the
frontend generators, so the semantic of "association" is captured once and
exposed to all consumers (API, frontend, CLI).
