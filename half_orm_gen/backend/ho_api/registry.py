"""
Registry for @ho_api_role dynamic role methods.

Usage in a relation module:
    from half_orm_gen.backend.ho_api import ho_api_role

    class Post(BasePost):
        @ho_api_role('author')
        async def _author_posts(self, request) -> list:
            self.author_id.set(request.state.user_id)
            return [elt['id'] async for elt in self.ho_aselect('id')]
"""

_ROLE_REGISTRY: dict[tuple[str, str, str], callable] = {}


def ho_api_role(name: str):
    """Decorator that registers a dynamic role method on a Relation subclass.

    The method receives (self, request) and returns a list of accessible PKs.
    Results are included in CRUD responses under the 'ho_roles' key.
    """
    def decorator(fn):
        fn._ho_api_role = name
        return fn
    return decorator


def register_relation_roles(cls):
    """Scan a Relation subclass for @ho_api_role methods and register them."""
    try:
        inst = cls()
        schema = inst._t_fqrn[1]
        table  = inst._t_fqrn[2]
    except Exception:
        return
    for attr in vars(cls).values():
        role_name = getattr(attr, '_ho_api_role', None)
        if role_name:
            _ROLE_REGISTRY[(schema, table, role_name)] = attr
