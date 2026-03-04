# half-orm-litestar

A [halfORM](https://github.com/collorg/halfORM) extension that generates a
[Litestar](https://litestar.dev) REST API from your halfORM relation classes
by decorating their methods.

## Installation

```bash
pip install half-orm-litestar
```

Requires `half-orm-dev` to be installed (for project introspection):

```bash
pip install half-orm-dev
```

---

## Quick start

### 1. Decorate your halfORM methods

In any halfORM relation class, import `tools` and annotate the methods you
want to expose as API routes:

```python
# myproject/actor/user.py

from half_orm_litestar import tools

class User(MODEL.get_relation_class('actor.user')):

    @tools.api_get('/user/{id: uuid}', guards=['public'])
    async def get_user(self, request: "Request"):
        actor_id = request.path_params['id']
        return self.load_user(actor_id)

    @tools.api_get('/user/{user_id: uuid}/group_accesses', guards=['has_user_access'])
    async def get_user_group_accesses(self, request: "Request"):
        actor_id = request.path_params['user_id']
        return [dict(row) for row in self.rfk_group_accesses(actor_id=actor_id)]

    @tools.api_post('/users', guards=['connected'])
    async def create_user(self, request: "Request"):
        data = await request.json()
        ...
```

The decorators accept the same arguments as the corresponding Litestar
decorators (`@get`, `@post`, `@put`, `@patch`, `@delete`).

Available decorators:

| Decorator          | HTTP method |
|--------------------|-------------|
| `tools.api_get`    | GET         |
| `tools.api_post`   | POST        |
| `tools.api_put`    | PUT         |
| `tools.api_patch`  | PATCH       |
| `tools.api_delete` | DELETE      |

### 2. Generate the API

From the root of your `half-orm-dev` project:

```bash
half_orm litestar generate
```

This command:

1. Scans all halfORM relation classes for `@api_*` decorated methods.
2. Creates missing scaffolding files in `api/` (only on first run — existing
   files are never overwritten).
3. Writes `api/main.py`, the ready-to-run Litestar application.

### 3. Run the API

```bash
uvicorn api.main:application --reload
```

---

## Project structure after `generate`

```
myproject/
├── api/
│   ├── __init__.py
│   ├── guards.py                        ← authentication guards (edit this)
│   ├── main.py                          ← generated, do not edit by hand
│   └── custom/
│       ├── __init__.py
│       ├── routes.py                    ← hand-written extra routes
│       └── middlewares/
│           ├── __init__.py              ← extra middlewares list
│           └── authorization.py        ← authentication middleware (edit this)
```

Files in `api/` (except `main.py`) are created once and never overwritten.
Regenerating only rewrites `main.py`.

---

## Customisation

### Guards (`api/guards.py`)

Guards are async callables that receive the ASGI connection and raise an
exception to deny access.  Two minimal guards are provided out of the box:
`public` (allow all) and `connected` (require authenticated user).

Add your own project-specific guards in `api/guards.py`:

```python
# api/guards.py
from litestar.connection import ASGIConnection
from litestar.handlers.base import BaseRouteHandler
from litestar.exceptions import HTTPException

async def has_user_access(
    connection: ASGIConnection, handler: BaseRouteHandler = None
) -> None:
    """Allow only the user identified by the ``user_id`` path parameter."""
    if not connection.user:
        raise HTTPException(status_code=401)
    if connection.user != str(connection.path_params.get('user_id')):
        raise HTTPException(status_code=403)
```

Then reference the guard by name in your decorator:

```python
@tools.api_get('/user/{user_id: uuid}/profile', guards=['has_user_access'])
async def get_profile(self, request: "Request"):
    ...
```

### Authorization middleware (`api/custom/middlewares/authorization.py`)

Implement the `Authorization` class to decode tokens / sessions and populate
`connection.user`.  When the file exists, `Authorization` is automatically
placed first in the middleware stack.

```python
# api/custom/middlewares/authorization.py
import jwt
from litestar.middleware import AbstractAuthenticationMiddleware, AuthenticationResult
from litestar.connection import ASGIConnection

SECRET = "change-me"

class Authorization(AbstractAuthenticationMiddleware):
    async def authenticate_request(self, connection: ASGIConnection) -> AuthenticationResult:
        token = (
            connection.headers.get("Authorization", "")
            .removeprefix("Bearer ")
            .strip()
        )
        try:
            payload = jwt.decode(token, SECRET, algorithms=["HS256"])
            return AuthenticationResult(user=payload["sub"], auth=token)
        except Exception:
            return AuthenticationResult(user=None, auth=None)
```

### Extra routes (`api/custom/routes.py`)

Hand-written Litestar route handlers can be added here:

```python
# api/custom/routes.py
from litestar import get

@get('/health')
async def health_check() -> dict:
    return {'status': 'ok'}

routes = [health_check]
```

### Extra middlewares (`api/custom/middlewares/__init__.py`)

```python
# api/custom/middlewares/__init__.py
from .my_middleware import MyMiddleware

middlewares = [MyMiddleware]
```

---

## Path prefix

The generated routes are automatically prefixed with the project's database
name.  For a project named `mydb`, `'/user/{id: uuid}'` becomes
`'/mydb/user/{id: uuid}'`.

---

## Advanced: using without `half-orm-dev`

`GenApi` can be used programmatically without a `Repo` object by supplying the
relation classes directly:

```python
from half_orm_litestar.generate import GenApi

GenApi(
    relation_classes=my_classes,   # iterable of (RelationClass, type) pairs
    module_name='mydb',
    base_dir='/path/to/project',
)
```