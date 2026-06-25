"""
Scaffold ho_api/app.py for a Litestar-backed halfORM project.

app.py is always regenerated. Developer customisations go in:
  ho_api/custom/middlewares/authorization.py  — defines Authorization middleware
  ho_api/custom/middlewares/__init__.py        — exposes extra `middlewares` list
  ho_api/custom/routes.py                      — exposes a `routes` list
These files are never touched by the generator.
"""

from pathlib import Path

_APP_TEMPLATE = """\
import os
import sys

cur_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, cur_dir)
par_dir = os.path.join(cur_dir, os.path.pardir)
sys.path.insert(0, par_dir)

from half_orm_gen.backend.litestar.v2.runtime import build_crud_app
from {module_name} import MODEL

_middleware: list = []
_route_handlers: list = []

try:
    from ho_api.custom.middlewares.authorization import Authorization
    _middleware = [Authorization]
except ImportError:
    pass

try:
    from ho_api.custom.middlewares import middlewares as _extra_middleware
    _middleware = _middleware + _extra_middleware
except ImportError:
    pass

try:
    from ho_api.custom.routes import routes as _route_handlers
except ImportError:
    pass

application = build_crud_app(
    MODEL,
    module_name='{module_name}',
    api_version={api_version},
    middleware=_middleware,
    route_handlers=_route_handlers,
)
"""


def scaffold_api_dir(
    api_dir: Path,
    module_name: str = '',
    api_version: int | None = None,
) -> None:
    """Write ho_api/app.py. Always regenerated — never protected."""
    app_py = api_dir / 'app.py'
    app_py.parent.mkdir(parents=True, exist_ok=True)
    version_str = str(api_version) if api_version is not None else 'None'
    content = (
        _APP_TEMPLATE
        .replace('{module_name}', module_name)
        .replace('{api_version}', version_str)
    )
    app_py.write_text(content, encoding='utf-8')
    print(f'  updated  {app_py}')
