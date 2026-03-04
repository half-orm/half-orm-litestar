"""
half-orm-litestar — Litestar API generation for halfORM projects.

Decorate halfORM relation methods with ``@tools.api_*`` and run
``half_orm litestar generate`` to produce a ready-to-run Litestar application.

Quick start::

    from half_orm_litestar import tools

    class MyTable(MODEL.get_relation_class('schema.my_table')):

        @tools.api_get('/items/{id: uuid}', guards=['connected'])
        async def get_item(self, request: "Request"):
            ...
"""