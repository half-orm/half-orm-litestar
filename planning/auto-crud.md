# Plan : Auto-CRUD API depuis le modèle half-orm

## Vision

`app.py` est le **maillon central d'une chaîne de génération full-stack** :

```
Schéma PostgreSQL
    ↓ half-orm-dev
Classes Python + ho_typeddicts + ho_baseclasses
    ↓ half-orm-litestar generate
api/app.py  ←  CRUD complet + contrôle d'accès + spec OpenAPI
    ↓ half-orm-angular / half-orm-svelte / ...
Stores front-end + client HTTP typé
```

Les générateurs front-end (Angular, Svelte, …) consommeront la spec OpenAPI produite par `app.py` pour générer les stores et clients d'API de façon entièrement automatisée.

**Conséquence** : la structure de `app.py` doit être **prévisible et stable** — routes canoniques, types bien définis — parce que d'autres générateurs s'y appuient.

### Évolution architecturale

Le CRUD généré automatiquement **devient** `app.py`, aux côtés des routes `@api_*` existantes. Les deux mécanismes coexistent et sont complémentaires :

| Mécanisme | Cas d'usage |
|---|---|
| Auto-CRUD (généré depuis `_ho_fields`) | Opérations standard sur une relation unique |
| `@api_*` (décoré sur les classes Relation) | Logique métier complexe : transactions multi-tables, insertions en cascade, validations croisées |
| `api/custom/routes.py` | Endpoints sans relation directe avec le modèle (agrégations, webhooks, …) |

Pour les relations qui ont des méthodes `@api_*`, le générateur skip la génération auto-CRUD sur les verbes déjà couverts. La route `@api_*` s'applique avec les droits définis sur son décorateur (guards) — `CRUD_ACCESS` ne s'applique qu'aux routes auto-générées.

---

## Contexte immédiat

`half_orm litestar generate` produit `api/app.py` en scannant les méthodes décorées `@api_*` sur les classes Relation. L'idée est d'aller plus loin : générer automatiquement des routes CRUD complètes pour **toutes les relations** du modèle, sans décorateur manuel, sur la base de l'introspection seule.

Ce document est une exploration des problèmes à résoudre avant implémentation.

---

## Ce que l'introspection fournit

Pour chaque relation, via `repo.model.classes()` :

| Attribut | Contenu |
|---|---|
| `relation._t_fqrn` | `(db, schema, table)` |
| `relation._ho_fields` | `dict[str, Field]` — colonnes et types Python |
| `relation._ho_pkey` | `dict[str, Field]` — colonnes PK |
| `relation._ho_kind` | `'Table'`, `'View'`, `'Materialized View'` |
| `relation._ho_dataclass_name()` | `'DC_SchemaTable'` |
| `field.py_type` | Type Python de la colonne (`int`, `str`, `datetime`, …) |

Opérations async disponibles sur chaque instance :
- `ho_aselect()` → async generator de `dict`
- `ho_ainsert()` → `dict`
- `ho_aupdate(**kwargs)` → `list[dict]`
- `ho_adelete()` → `list[dict]`

---

## Routes à générer par relation

| Méthode | Route | Tables | Views |
|---|---|---|---|
| GET | `/vN/schema/table` | ✓ (filtres via query params) | ✓ |
| GET | `/vN/schema/table/{pk}` | ✓ (si PK simple) | ✓ (si PK simple) |
| POST | `/vN/schema/table` | ✓ | ✗ |
| PUT | `/vN/schema/table/{pk}` | ✓ (si PK simple) | ✗ |
| DELETE | `/vN/schema/table/{pk}` | ✓ (si PK simple) | ✗ |

**PK composite ou absente** → GET list uniquement (pas de routes `/{pk}`).

---

## Problèmes à résoudre

### 1. Schémas d'entrée/sortie ✓ résolu

Les `DC_PublicNode` etc. ont un `__post_init__` qui **remet tous les champs à None** après construction — inutilisables pour porter des données réelles.

**Solution** : `ho_typeddicts.py`, déjà généré par `half-orm-dev` aux côtés de `ho_baseclasses.py`, contient un `TypedDict` par relation (`total=False` — tous les champs optionnels) :

```python
class PublicNodeDict(TypedDict, total=False):
    id: Optional[int]
    name: Optional[str]
    type: Optional[int]
    ...
```

Il suffit de l'importer dans `app.py` comme `ho_baseclasses` l'est déjà :

```python
from {module} import ho_typeddicts
```

Les handlers utilisent directement `ho_typeddicts.PublicNodeDict` en entrée et en sortie. Les dicts retournés par `ho_aselect()` / `ho_ainsert()` satisfont nativement le TypedDict — aucune conversion nécessaire.

### 3. GET list : filtrage, projection et pagination

`ho_aselect` a deux mécanismes distincts :

- **Filtrage** : contraintes posées sur le constructeur `Relation(**filter_kwargs)` — un champ = une contrainte d'égalité SQL
- **Projection** (`*data_filters`) : liste de noms de colonnes à retourner — `ho_aselect('id', 'name')` → `SELECT id, name ...`
- **Pagination** : `ho_aselect(limit=N, offset=M)`

Le handler généré expose tout via query params :

```python
@get("/v0/anonymous/node")
async def _auto_public_node_list(
    # filtres (un par colonne, générés depuis _ho_fields)
    id: Optional[int] = None,
    name: Optional[str] = None,
    type: Optional[int] = None,
    # projection : colonnes à retourner (ex: ?fields=id&fields=name)
    fields: Optional[List[str]] = None,
    # pagination
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> list[ho_typeddicts.PublicNodeDict]:
    filter_kwargs = {k: v for k, v in {'id': id, 'name': name, 'type': type}.items() if v is not None}
    data_filters = fields or []
    return [
        row async for row in public_node.Node(**filter_kwargs).ho_aselect(
            *data_filters, limit=limit, offset=offset
        )
    ]
```

**Problème ouvert** : pour une relation avec beaucoup de colonnes, la signature devient longue. C'est acceptable pour du code généré (OpenAPI documente tout automatiquement), mais à surveiller.

### 4. Gestion des erreurs

- `GET /{pk}` : si aucune ligne → `HTTPException(404)`
- `PUT /{pk}` : si `ho_aupdate` retourne liste vide → `HTTPException(404)`
- `DELETE /{pk}` : idem
- `POST` : si violation de contrainte PG (unicité, FK) → capturer `psycopg.errors.*` et retourner `HTTPException(409)` ou `422`

### 5. Accès et sécurité — problème central

Puisque tout est exposé, le contrôle d'accès devient **la** pièce maîtresse. Granularité nécessaire :

| Niveau | Exemple | Mécanisme |
|---|---|---|
| Relation | `admin.config` entièrement bloquée | absence dans `ACCESS` |
| Opération | GET accessible, DELETE non | opération absente du dict |
| Champ (lecture) | `password_hash` jamais retourné | liste de champs par rôle |
| Champ (écriture) | un `connected` ne peut pas écrire `admin_flag` | liste de champs par rôle |
| Ligne | un user voit uniquement ses propres données | PostgreSQL RLS |

Les niveaux ligne sont délégués à PostgreSQL (RLS, vues restreintes). Les niveaux relation, opération et champ sont dans `crud_access.py`.

#### Système de rôles : `api/roles/`

Les rôles sont définis dans un **répertoire** `api/roles/`, un module par rôle. Chaque module expose une seule fonction :

```python
async def authorize(path_params: dict, jwt_payload: ProxyJWTPayload) -> bool
```

La chaîne de base obligatoire : `anonymous → connected → rôle spécifique`

Les rôles `anonymous` et `connected` sont des **cas spéciaux** gérés directement dans le checker d'autorisation (pas besoin de module) :

- `anonymous` → toujours `True`
- `connected` → `True` si `jwt_payload.user_id` est présent, sinon `False` (court-circuit : inutile de vérifier les rôles spécifiques)

Pour les autres rôles, le checker charge dynamiquement `api.roles.{role_name}` et appelle `authorize()`.

```
api/
  roles/
    membre.py         # créé par le développeur
    permanent.py      # créé par le développeur — raffine membre
    admin.py          # créé par le développeur
```

La composition de rôles se fait via deux décorateurs fournis par `api/roles/core.py` :

- `@authorize_and(role_name)` — **refinement** : les deux conditions doivent être vraies (implémente "X est un Y")
- `@authorize_or(role_name)` — **alternative** : l'une ou l'autre suffit

```python
# api/roles/membre.py
from api.schemas.jwt import ProxyJWTPayload

async def authorize(path_params: dict, jwt_payload: ProxyJWTPayload) -> bool:
    return jwt_payload.is_membre

# api/roles/permanent.py — un permanent est aussi un membre (AND)
from api.roles.core import authorize_and
from api.schemas.jwt import ProxyJWTPayload

@authorize_and("membre")
async def authorize(path_params: dict, jwt_payload: ProxyJWTPayload) -> bool:
    return jwt_payload.is_permanent

# api/roles/admin_ou_responsable.py — accès alternatif (OR)
from api.roles.core import authorize_or
from api.schemas.jwt import ProxyJWTPayload

@authorize_or("responsable")
async def authorize(path_params: dict, jwt_payload: ProxyJWTPayload) -> bool:
    return jwt_payload.is_admin  # True si admin OU responsable
```

Un rôle peut aussi faire des vérifications par ligne (row-level) :

```python
# api/roles/auteur.py — propriétaire d'une ressource spécifique
from half_orm.relation_errors import MultipleRowsError, NotFoundError
from api.roles.core import authorize_and
from api.schemas.jwt import ProxyJWTPayload
from mydb.anonymous.project import Project

@authorize_and("connected")   # doit d'abord être connecté
async def authorize(path_params: dict, jwt_payload: ProxyJWTPayload) -> bool:
    project_id = path_params.get("project_id")
    try:
        return Project(id=project_id).has_user(jwt_payload.user_id)
    except (NotFoundError, MultipleRowsError):
        return False
```

`api/roles/core.py` (scaffoldé, jamais régénéré) expose `authorize_and` et `authorize_or`.

#### Checker d'autorisation

Le checker est une méthode de classe (sur le middleware d'autorisation). Il consulte `__route_role_names`, un dict `(method, route_path) → [role_names]` alimenté au démarrage depuis `crud_access.py` :

```python
@classmethod
async def _check_route_authorization(
    cls, method: str, route_path: str, request_like, jwt_payload: ProxyJWTPayload,
) -> bool:
    route_role_names = cls.__route_role_names.get((method, route_path), [])

    if "anonymous" in route_role_names:
        return True

    if "connected" in route_role_names:
        return bool(jwt_payload.user_id)  # court-circuit

    for role_name in route_role_names:
        try:
            role_module = importlib.import_module(f"api.roles.{role_name}")
            if await role_module.authorize(request_like.path_params, jwt_payload):
                return True
        except (ModuleNotFoundError, AttributeError):
            continue  # loggé en warning

    return False
```

#### Définition des accès : dans les modules générés par `half-orm-dev`

Plutôt qu'un fichier central `crud_access.py`, les accès sont définis **dans l'espace développeur** de chaque module généré par `half-orm-dev`. Ces espaces sont préservés lors des régénérations.

```python
# mydb/anonymous/node.py  (généré par half-orm-dev, espace dev préservé)

from mydb.ho_baseclasses import HoPublicNode

# --- espace développeur (jamais écrasé) ---

CRUD_ACCESS = {
    "GET": {
        "anonymous":    ["id", "name", "type"],
        "membre":    ["id", "name", "type", "level", "infoid"],
        "permanent": None,   # None = tous les champs
        "admin":     None,
    },
    "POST": {
        "membre":    ["name", "type"],
        "admin":     None,
    },
    "PUT": {
        "permanent": ["name", "type"],
        "admin":     None,
    },
    "DELETE": {
        "admin":     None,
    },
    # verbe absent = opération non accessible
}

class Node(HoPublicNode):
    pass

# --- fin espace développeur ---
```

**Avantages :**
- Accès co-localisés avec la relation → cohérence et lisibilité
- Survivent aux régénérations `half-orm-dev`
- Absence de `CRUD_ACCESS` dans un module = relation entièrement bloquée (deny-by-default)

`half_orm litestar generate` lit `CRUD_ACCESS` sur chaque module via `getattr(module, 'CRUD_ACCESS', None)` et construit `__route_role_names` à la génération.

Le middleware réalise deux étapes distinctes :

**Étape 1 — autorisation de la route** (`_check_route_authorization`) : retourne True/False. Peut court-circuiter sur `anonymous` (toujours True) ou `connected` (True si authentifié, sinon False sans évaluer les rôles domaine).

**Étape 2 — calcul des rôles autorisés** : évalue **tous** les rôles déclarés pour l'opération et collecte ceux qui retournent True. Stocké dans `request.state.authorized_roles` pour usage dans le handler.

```python
# Étape 2 dans le middleware (après autorisation confirmée)
async def _compute_authorized_roles(cls, verb, module_crud_access, request_like, jwt_payload):
    role_access = module_crud_access.get(verb, {})
    authorized = []
    for role_name in role_access:
        if role_name == "anonymous":
            authorized.append(role_name)
        elif role_name == "connected":
            if jwt_payload.user_id:
                authorized.append(role_name)
        else:
            try:
                role_module = importlib.import_module(f"api.roles.{role_name}")
                if await role_module.authorize(request_like.path_params, jwt_payload):
                    authorized.append(role_name)
            except (ModuleNotFoundError, AttributeError):
                pass
    return authorized

request.state.authorized_roles = await _compute_authorized_roles(...)
```

Le handler calcule l'**union des champs** de tous les rôles autorisés :

```python
# Dans le handler généré
@get("/v0/anonymous/node")
async def _auto_public_node_list(request: Request, ...) -> list[ho_typeddicts.PublicNodeDict]:
    authorized = request.state.authorized_roles
    role_fields = public_node.CRUD_ACCESS["GET"]
    if any(role_fields.get(r) is None for r in authorized):
        allowed = []  # pas de projection = tous les champs
    else:
        allowed = list({f for r in authorized for f in (role_fields.get(r) or [])})
    ...
```

Propriétés :
- **Order-independent** : l'union est commutative, l'ordre de déclaration ne compte pas
- **Additif** : `anonymous` + `membre` → union des champs des deux rôles (un membre voit tout ce que anonymous voit + ses champs supplémentaires)
- **Sûr** : si `authorized_roles` est vide → le guard a déjà refusé en amont (HTTP 403)

### 6. Cycle de vie

- `generate` → génère **toujours** `api/app.py` — pas de flag, pas d'option
- `api/crud_access.py` est scaffoldé à la première génération (toutes les relations avec accès vide = tout bloqué), puis édité à la main et jamais écrasé
- `api/custom/routes.py` reste pour les endpoints non-CRUD

---

## Structure du code généré (esquisse)

L'exemple ci-dessous montre ce que `half_orm litestar generate` produit pour la relation `anonymous.node` (table, PK simple `id: int`).

```python
# Extrait de api/app.py — généré, ne pas éditer

from jdmml import ho_typeddicts
from jdmml.anonymous import node as public_node
from api import crud_access


def _effective_fields(relation: str, verb: str, authorized_roles: list[str]) -> list[str]:
    """Union des champs autorisés pour l'ensemble des rôles validés.

    Retourne [] si au moins un rôle a None (= tous les champs, pas de projection).
    """
    role_fields = crud_access.ACCESS.get(relation, {}).get(verb, {})
    if any(role_fields.get(r) is None for r in authorized_roles):
        return []
    return list({f for r in authorized_roles for f in (role_fields.get(r) or [])})


def _writable_fields(data: dict, relation: str, verb: str, authorized_roles: list[str]) -> dict:
    """Filtre le dict entrant aux seuls champs que le rôle peut écrire."""
    allowed = _effective_fields(relation, verb, authorized_roles)
    if not allowed:
        return data
    return {k: v for k, v in data.items() if k in allowed}


# GET /v0/anonymous/node — liste avec filtres, projection client et pagination
@get("/v0/anonymous/node")
async def _auto_public_node_list(
    request: Request,
    id: Optional[int] = None,
    name: Optional[str] = None,
    type: Optional[int] = None,
    fields: Optional[List[str]] = None,   # projection demandée par le client
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> list[ho_typeddicts.PublicNodeDict]:
    filter_kwargs = {k: v for k, v in {'id': id, 'name': name, 'type': type}.items() if v is not None}
    authorized = _effective_fields("anonymous.node", "GET", request.state.authorized_roles)
    if fields:
        # intersection : ce que le client demande ∩ ce que son rôle autorise
        projection = [f for f in fields if not authorized or f in authorized]
    else:
        projection = authorized  # [] = ho_aselect() sans args = tous les champs autorisés
    return [
        row async for row in public_node.Node(**filter_kwargs).ho_aselect(
            *projection, limit=limit, offset=offset
        )
    ]


# GET /v0/anonymous/node/{id} — enregistrement unique par PK
@get("/v0/anonymous/node/{id: int}")
async def _auto_public_node_get(
    request: Request,
    id: int,
) -> ho_typeddicts.PublicNodeDict:
    authorized = _effective_fields("anonymous.node", "GET", request.state.authorized_roles)
    rows = [row async for row in public_node.Node(id=id).ho_aselect(*authorized)]
    if not rows:
        raise HTTPException(status_code=404)
    return rows[0]


# POST /v0/anonymous/node — création
@post("/v0/anonymous/node")
async def _auto_public_node_create(
    request: Request,
    data: ho_typeddicts.PublicNodeDict,
) -> ho_typeddicts.PublicNodeDict:
    writable = _writable_fields(dict(data), "anonymous.node", "POST", request.state.authorized_roles)
    return await public_node.Node(**writable).ho_ainsert()


# PUT /v0/anonymous/node/{id} — mise à jour partielle
@put("/v0/anonymous/node/{id: int}")
async def _auto_public_node_update(
    request: Request,
    id: int,
    data: ho_typeddicts.PublicNodeDict,
) -> ho_typeddicts.PublicNodeDict:
    payload = {k: v for k, v in dict(data).items() if v is not None}
    writable = _writable_fields(payload, "anonymous.node", "PUT", request.state.authorized_roles)
    result = await public_node.Node(id=id).ho_aupdate(**writable)
    if not result:
        raise HTTPException(status_code=404)
    return result[0]


# DELETE /v0/anonymous/node/{id} — suppression
@delete("/v0/anonymous/node/{id: int}")
async def _auto_public_node_delete(
    request: Request,
    id: int,
) -> None:
    result = await public_node.Node(id=id).ho_adelete()
    if not result:
        raise HTTPException(status_code=404)
```

---

## Organisation du code

`generate.py` actuel deviendrait ingérable avec la génération CRUD. Découpage en modules à responsabilité unique :

```
half_orm_litestar/
  generate.py       # GenApi : orchestrateur uniquement
  templates.py      # toutes les chaînes _*_TEMPLATE
  scaffold.py       # _scaffold_api_dir, scaffold api/roles/core.py
  api_routes.py     # génération depuis @api_* (logique actuelle extraite)
  crud_routes.py    # génération CRUD depuis CRUD_ACCESS + _ho_fields/_ho_pkey/_ho_kind
```

## Fichiers à créer / modifier

| Fichier | Action |
|---|---|
| `half_orm_litestar/templates.py` | Créer — extraire tous les templates de `generate.py` |
| `half_orm_litestar/scaffold.py` | Créer — extraire `_scaffold_api_dir`, ajouter scaffold `roles/core.py` |
| `half_orm_litestar/api_routes.py` | Créer — extraire la logique `@api_*` de `generate.py` |
| `half_orm_litestar/crud_routes.py` | Créer — génération CRUD depuis `CRUD_ACCESS` + introspection |
| `half_orm_litestar/generate.py` | Refactorer en orchestrateur mince |
| `half_orm_litestar/cli_extension.py` | Aucun changement |
| `tests/test_extension.py` | Nouveaux tests pour CRUD, projection par rôle, `_effective_fields` |

---

