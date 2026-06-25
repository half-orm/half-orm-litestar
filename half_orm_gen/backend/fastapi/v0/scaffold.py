"""
Scaffold ho_api/app.py for a FastAPI-backed halfORM project.

app.py is always regenerated. Developer customisations go in:
  ho_api/custom/routes.py  — exposes an APIRouter as `router`
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

from half_orm_gen.backend.fastapi.v0.runtime import build_crud_app
from {module_name} import MODEL

_extra_routers: list = []

try:
    from ho_api.custom.routes import router as _custom_router
    _extra_routers = [_custom_router]
except ImportError:
    pass

application = build_crud_app(
    MODEL,
    module_name='{module_name}',
    api_version={api_version},
    extra_routers=_extra_routers,
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
