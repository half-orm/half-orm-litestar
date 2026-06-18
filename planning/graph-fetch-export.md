# Graph Fetch & Export

## Contexte

Lors de l'implémentation des broadcasts WS en cascade (`_ws_broadcast_cascade`),
on a observé que la traversée des reverse FKs d'un objet halfORM permet de
récupérer l'intégralité des objets dépendants. En ajoutant les FKs directes
(références parentales), on obtient le graphe connexe complet d'une instance.

## Idée

Deux endpoints auto-générés pour chaque ressource disposant d'un `CRUD_ACCESS` :

```
GET /{resource}/{id}/graph    → deep fetch (JSON)
GET /{resource}/{id}/export   → même payload, Content-Disposition: attachment
```

## Structure du payload

Représentation plate par ressource, réimportable directement :

```json
{
  "blog/author":       [{ "id": "a1", "name": "..." }],
  "blog/post":         [{ "id": "p1", "author_id": "a1", ... }],
  "blog/comment":      [{ "id": "c1", "post_id": "p1", ... }],
  "blog/comment_type": [{ "id": "ct1", ... }]
}
```

## Traversée

La logique existante de `_ws_broadcast_cascade` ne descend que via les
**reverse FKs** (enfants/dépendants). Pour un graph fetch complet, on traverse
les **deux directions** avec détection de cycles :

- `is_reverse = True`  → enfants (posts d'un auteur, commentaires d'un post)
- `is_reverse = False` → parents (auteur d'un post, type d'un commentaire)

Prototype Python (backend, à générer dans `crud_routes.py`) :

```python
async def _ho_graph(inst, resource: str, pk_val, _seen: set | None = None) -> dict:
    if _seen is None:
        _seen = set()
    _key = (resource, str(pk_val))
    if _key in _seen:
        return {}
    _seen.add(_key)

    result = {resource: [await ...ho_aselect(...)]}  # l'objet lui-même

    for _fk in inst._ho_fkeys().values():
        _fk_field = _fk.fk_names[0] if len(_fk.fk_names) == 1 else None
        if not _fk_field:
            continue
        _fqtn = _fk.remote['fqtn']
        _r    = f"{_fqtn[0].replace('.', '_')}/{_fqtn[1]}"
        if _r not in _WS_RMAP:
            continue
        _cls, _pk = _WS_RMAP[_r]

        if _fk.is_reverse:
            # enfants : tous les objets qui référencent pk_val
            for _row in await _cls(**{_fk_field: pk_val}).ho_aselect(_pk):
                sub = await _ho_graph(_cls(**{_pk: _row[_pk]}), _r, _row[_pk], _seen)
                for k, v in sub.items():
                    result.setdefault(k, []).extend(v)
        else:
            # parent : l'objet référencé par inst
            parent_id = getattr(inst, _fk_field, None) or ...  # lire depuis l'instance
            if parent_id:
                sub = await _ho_graph(_cls(**{_pk: parent_id}), _r, parent_id, _seen)
                for k, v in sub.items():
                    result.setdefault(k, []).extend(v)

    return result
```

## Questions ouvertes

1. **Profondeur des FKs directes** — remonter jusqu'à la racine (pas de FK directe),
   ou se limiter aux parents immédiats pour éviter de rapatrier trop de données ?

2. **Autorisation** — appliquer `CRUD_ACCESS GET` de chaque ressource traversée
   (cohérent avec le reste), ou traiter l'export comme une opération privilégiée
   distincte (rôle `export` dédié) ?

3. **Import** — prévoir un endpoint `POST /{version}/import` qui accepte ce
   format et insère dans l'ordre topologique (parents avant enfants).

4. **Format d'export** — JSON brut suffit pour un transfert entre environnements ;
   JSON-LD ou HAL pourraient apporter de la sémantique mais complexifient l'import.

## Réutilisation de `_WS_RMAP`

Le dictionnaire `_WS_RMAP` déjà généré dans `crud_routes.py` mappe
`"schema/table"` → `(cls, pk_field)` — exactement ce qu'il faut pour
instancier les classes halfORM lors de la traversée.
