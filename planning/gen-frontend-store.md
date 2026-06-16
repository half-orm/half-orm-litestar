# Plan : `half_orm litestar gen-store`

## Contexte

`generate` produit `api/app.py` avec une `_ACCESS_MAP` complète et un endpoint
`GET /vN/ho_access` filtré par rôle. L'étape suivante est de générer côté front
les stores et les appels API correspondants, à partir des mêmes données
d'introspection Python (sans appeler le serveur).

La commande sera extensible dès le départ pour accueillir plusieurs frameworks
(Svelte, Angular/NgRx, Vue/Pinia…).

---

## Commande CLI

```
half_orm litestar gen-store --svelte [--output frontend/svelte]
```

- `--svelte` (flag) : active le générateur Svelte (obligatoire pour l'instant)
- `--output <dir>` : répertoire de sortie, défaut `frontend/svelte`
- Structure extensible : `--ngrx`, `--pinia` etc. activeront leurs propres générateurs

---

## Architecture des fichiers à créer / modifier

```
half_orm_litestar/gen_store/
├── __init__.py        ← GenStore orchestrateur (classe principale)
├── base.py            ← StoreGenerator : classe abstraite + utilitaires partagés
└── svelte.py          ← SvelteGenerator : génération TypeScript/Svelte

half_orm_litestar/cli_extension.py   ← ajout de la commande gen-store
```

Sortie générée (exemple blog) :

```
frontend/svelte/
├── config.ts          ← BASE_URL configurable (généré une seule fois)
├── blog_author.ts
├── blog_post.ts
├── blog_comment.ts
├── blog_comment_type.ts
└── index.ts           ← re-exports + hoAccess() + setApiBaseUrl()
```

---

## Réutilisation du code existant (crud_routes.py)

| Fonction | Rôle |
|----------|------|
| `_gen_out_fields(crud_access, verb, api_excluded, all_names)` | champs de sortie pour les interfaces Out |
| `_gen_in_fields(crud_access, verb, pk_field, api_excluded, all_names)` | champs d'entrée pour PostIn / PutIn |
| `_simple_pk(relation)` | présence et type de la PK simple |
| `_instance(relation)` | instanciation pour accéder à `_ho_fields` |
| `_py_type_str(py_type)` | string Python qualifié (réutilisé pour le mapping TS) |

Import direct depuis `half_orm_litestar.crud_routes`.

---

## base.py — StoreGenerator (classe abstraite)

```python
class StoreGenerator:
    PY_TO_TS = {
        'str': 'string', 'int': 'number', 'float': 'number',
        'bool': 'boolean', 'uuid.UUID': 'string',
        'datetime.datetime': 'string', 'datetime.date': 'string',
        'datetime.time': 'string', 'datetime.timedelta': 'string',
        'decimal.Decimal': 'number',
    }

    def ts_type(self, py_type) -> str: ...          # PY_TO_TS lookup, défaut 'unknown'
    def resource_name(self, schema, table) -> str:  # blogAuthor (camelCase)
    def interface_name(self, schema, table) -> str: # BlogAuthor (PascalCase)

    def generate(self, classes, api_version, output_dir: Path): ...  # à implémenter
```

---

## svelte.py — SvelteGenerator

Pour chaque relation ayant `CRUD_ACCESS` :

1. Récupère `api_excluded`, `all_fields`, `pk_info` via les helpers de `crud_routes`
2. Calcule les champs Out, PostIn, PutIn (génération-time, tous rôles en union)
3. Génère le fichier `.ts` :

```typescript
// frontend/svelte/blog_author.ts
import { writable } from 'svelte/store';

export interface BlogAuthorOut    { id: string; name: string; email: string }
export interface BlogAuthorPostIn { name: string; email: string }
export interface BlogAuthorPutIn  { name: string; email: string }

export const blogAuthorStore = writable<BlogAuthorOut[]>([]);

const _BASE = '/v0/blog/author';

export const blogAuthorApi = {
    list:   (params: Partial<BlogAuthorOut> = {}) =>
                fetch(_BASE + '?' + new URLSearchParams(params as any)),
    get:    (id: string) => fetch(`${_BASE}/${id}`),
    create: (data: BlogAuthorPostIn) =>
                fetch(_BASE, { method: 'POST',
                               headers: {'Content-Type': 'application/json'},
                               body: JSON.stringify(data) }),
    update: (id: string, data: BlogAuthorPutIn) =>
                fetch(`${_BASE}/${id}`, { method: 'PUT',
                                          headers: {'Content-Type': 'application/json'},
                                          body: JSON.stringify(data) }),
    remove: (id: string) => fetch(`${_BASE}/${id}`, { method: 'DELETE' }),
};
```

- Verbes absents du `CRUD_ACCESS` → omis de l'objet `api`
- Relation sans PK simple → pas de `get` / `update` / `remove`

---

## index.ts — re-exports + hoAccess

```typescript
// frontend/svelte/index.ts
export * from './blog_author';
export * from './blog_post';
// ...

export async function hoAccess(token?: string): Promise<Record<string, any>> {
    const headers: Record<string, string> = token
        ? { Authorization: `Bearer ${token}` }
        : {};
    const res = await fetch('/v0/ho_access', { headers });
    if (!res.ok) throw new Error(`ho_access: ${res.status}`);
    return res.json();
}
```

---

## __init__.py — GenStore orchestrateur

```python
class GenStore:
    def __init__(self, repo, *, generator: StoreGenerator, output_dir: Path, api_version):
        self._classes = list(repo.model.classes())
        generator.generate(self._classes, api_version, output_dir)
```

Même interface que `GenApi` pour cohérence.

---

## cli_extension.py — ajout de la commande

```python
@litestar.command('gen-store')
@click.option('--svelte', 'framework', flag_value='svelte', default=True)
@click.option('--output', default=None,
              help='Output directory (default: frontend/<framework>)')
def gen_store(framework, output):
    """Generate frontend stores from CRUD_ACCESS introspection."""
    ...
    from half_orm_litestar.gen_store import GenStore
    from half_orm_litestar.gen_store.svelte import SvelteGenerator
    output_dir = Path(output) if output else Path('frontend') / framework
    GenStore(repo, generator=SvelteGenerator(),
             output_dir=output_dir, api_version=api_version)
```

---

## Vérification

```bash
cd tests/e2e/scripts/blog_demo
half_orm litestar gen-store --svelte
# → frontend/svelte/blog_author.ts etc.
# → frontend/svelte/index.ts

# Contrôles manuels :
# - Interfaces Out/PostIn/PutIn cohérentes avec CRUD_ACCESS
# - Verbes absents bien omis de l'objet api
# - hoAccess() dans index.ts avec la bonne version /vN/
# - blog/comment_type (GET only, PK TEXT non-uuid) → list uniquement
```
