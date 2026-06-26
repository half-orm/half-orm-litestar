"""
half_orm_meta.api — persistent API access-control schema.

Public decorators:
    @ho_api_role(name)  — declare a dynamic role method on a Relation subclass
"""
from .registry import ho_api_role, _ROLE_REGISTRY

__all__ = ['ho_api_role', '_ROLE_REGISTRY']
