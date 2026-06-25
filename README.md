# half-orm-gen

> **⚠️ Alpha — not for production.**  
> This project is under active development. APIs, generated code structure, and CLI
> commands may change without notice between releases. Do not use in production
> environments.

A [halfORM](https://github.com/half-orm/half-orm) extension that generates a
[Litestar](https://litestar.dev) or [FastAPI](https://fastapi.tiangolo.com) REST API
**and** a frontend backoffice ([SvelteKit 5](https://svelte.dev) or
[Angular](https://angular.dev)) from your [half-orm-dev](https://github.com/half-orm/half-orm-dev) project.

## Installation

```bash
pip install half-orm-gen
```

---

## API

```bash
# Litestar
half_orm gen api --litestar
litestar --app ho_api/app:application run --reload

# FastAPI
half_orm gen api --fastapi
uvicorn ho_api.app:application --reload
```

---

## Frontend backoffice

```bash
# SvelteKit 5
half_orm gen frontend --svelte
cd ho_frontend/svelte && npm install && npm run dev

# Angular
half_orm gen frontend --angular
cd ho_frontend/angular && npm install && npm start
```

---

## Contributing

We are looking for contributors with expertise in:

- **Angular** — improve generated components, routing, and state management
- **SvelteKit** — improve generated stores, layouts, and page components
- **Litestar** — improve the dynamic runtime, middleware, and OpenAPI integration
- **FastAPI** — improve the dynamic runtime and Pydantic integration

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to set up a development environment
and the areas where help is most needed.

---

## Documentation

- [Backend architecture](docs/backend-architecture.md) — runtime, CRUD_ACCESS, role system, WebSocket
- [Frontend architecture](docs/frontend-architecture.md) — silo pattern, access map, live updates
- [Generated frontend code](docs/frontend-code-organization.md) — file layout, regenerated vs scaffolded
- [Angular silo architecture](docs/angular-silo-architecture.md)
- [Svelte silo architecture](docs/svelte-silo-architecture.md)

---

## See also

- [half-orm](https://github.com/half-orm/half-orm) — the PostgreSQL ORM at the core
- [half-orm-dev](https://github.com/half-orm/half-orm-dev) — the development framework
