"""
SvelteKit 5 POC application generator.

Produces a throwaway SvelteKit app (Tailwind + TypeScript + Svelte 5 runes)
with one list/detail/create page per CRUD_ACCESS resource.
"""

import importlib
import shutil
from pathlib import Path

from half_orm_litestar.crud_routes import (
    _gen_out_fields,
    _gen_in_fields,
    _simple_pk,
    _instance,
    _py_type_str,
)
from half_orm_litestar.gen_store.svelte import SvelteGenerator
from half_orm_litestar.gen_store.base import StoreGenerator


# ---------------------------------------------------------------------------
# Static file templates
# ---------------------------------------------------------------------------

_PACKAGE_JSON = """\
{{
  "name": "{project_name}",
  "version": "0.0.1",
  "private": true,
  "type": "module",
  "scripts": {{
    "dev": "vite dev",
    "build": "vite build",
    "preview": "vite preview",
    "check": "svelte-kit sync && svelte-check --tsconfig ./tsconfig.json",
    "check:watch": "svelte-kit sync && svelte-check --tsconfig ./tsconfig.json --watch"
  }},
  "devDependencies": {{
    "@sveltejs/adapter-auto": "^3.0.0",
    "@sveltejs/kit": "^2.0.0",
    "@sveltejs/vite-plugin-svelte": "^5.0.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "svelte": "^5.0.0",
    "svelte-check": "^4.0.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.0.0",
    "vite": "^6.0.0"
  }}
}}
"""

_SVELTE_CONFIG = """\
import adapter from '@sveltejs/adapter-auto';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

const config = {
  preprocess: vitePreprocess(),
  kit: { adapter: adapter() }
};

export default config;
"""

_VITE_CONFIG = """\
import {{ sveltekit }} from '@sveltejs/kit/vite';
import {{ defineConfig }} from 'vite';

export default defineConfig({{
  plugins: [sveltekit()],
  server: {{
    proxy: {{
      '{version_prefix}': 'http://localhost:8000',
    }}
  }}
}});
"""

_TSCONFIG = """\
{
  "extends": "./.svelte-kit/tsconfig.json",
  "compilerOptions": {
    "allowJs": true,
    "checkJs": true,
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "skipLibCheck": true,
    "sourceMap": true,
    "strict": true
  }
}
"""

_TAILWIND_CONFIG = """\
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: { extend: {} },
  plugins: []
};
"""

_POSTCSS_CONFIG = """\
export default {
  plugins: { tailwindcss: {}, autoprefixer: {} }
};
"""

_APP_HTML = """\
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <link rel="icon" href="%sveltekit.assets%/favicon.png" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    %sveltekit.head%
  </head>
  <body data-sveltekit-preload-data="hover">
    <div style="display: contents">%sveltekit.body%</div>
  </body>
</html>
"""

_APP_CSS = """\
@tailwind base;
@tailwind components;
@tailwind utilities;
"""

_AUTH_STORE = """\
class AuthState {
    token = $state<string | null>(
        typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('ho_token') : null
    );

    login(t: string) {
        sessionStorage.setItem('ho_token', t);
        this.token = t;
    }

    logout() {
        sessionStorage.removeItem('ho_token');
        this.token = null;
    }
}

export const auth = new AuthState();
"""

_LOGIN_PAGE = """\
<script lang="ts">
  import { auth } from '$lib/auth.svelte.ts';
  import { goto } from '$app/navigation';

  let tokenInput = $state('');

  function handleLogin() {
    if (tokenInput.trim()) {
      auth.login(tokenInput.trim());
      goto('/');
    }
  }
</script>

<div class="max-w-md mx-auto mt-12 p-6 bg-white rounded-lg shadow">
  <h1 class="text-2xl font-bold mb-6">Login</h1>
  <p class="text-sm text-gray-600 mb-4">Paste your JWT token:</p>
  <textarea
    bind:value={tokenInput}
    class="w-full h-32 border rounded p-2 font-mono text-sm mb-4"
    placeholder="eyJ..."
  ></textarea>
  <button
    onclick={handleLogin}
    class="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
  >
    Login
  </button>
</div>
"""

_HOME_PAGE = """\
<script lang="ts">
  import {{ goto }} from '$app/navigation';
  import {{ onMount }} from 'svelte';
  onMount(() => goto('{first_route}'));
</script>
"""


# ---------------------------------------------------------------------------
# Dynamic template helpers
# ---------------------------------------------------------------------------

def _title(schema_name: str, table_name: str) -> str:
    return ' '.join(p.capitalize() for p in (schema_name + '_' + table_name).split('_'))


def _layout(resources: list) -> str:
    nav_links = '\n    '.join(
        f'<a href="/{sn}/{tn}" class="hover:underline text-gray-700">{_title(sn, tn)}</a>'
        for sn, tn, *_ in resources
    )
    return f"""\
<script lang="ts">
  import '../app.css';
  import {{ auth }} from '$lib/auth.svelte.ts';

  let {{ children }} = $props();
</script>

<div class="min-h-screen bg-gray-50">
  <nav class="bg-white shadow-sm border-b px-6 py-3 flex gap-6 items-center">
    <span class="font-bold text-gray-800">API Browser</span>
    {nav_links}
    <div class="ml-auto flex gap-3 items-center">
      {{#if auth.token}}
        <span class="text-xs text-gray-500">authenticated</span>
        <button onclick={{auth.logout}} class="text-sm text-red-600 hover:underline">Logout</button>
      {{:else}}
        <a href="/login" class="text-sm text-blue-600 hover:underline">Login</a>
      {{/if}}
    </div>
  </nav>
  <main class="p-6">
    {{@render children()}}
  </main>
</div>
"""


def _list_page(
    schema_name: str, table_name: str,
    stem: str, rname: str, iname: str,
    out_names: list, pk_info,
    has_post: bool, has_del: bool,
    map_key: str,
) -> str:
    pk_field = pk_info[0] if pk_info else None
    pk_ts   = pk_info[1] if pk_info else 'string'  # litestar path type, not ts — use string
    title   = _title(schema_name, table_name)

    th_cols = '\n        '.join(
        f'<th class="px-4 py-2 text-left text-sm font-semibold text-gray-600">{f}</th>'
        for f in out_names
    )
    td_cols = '\n          '.join(
        f'<td class="px-4 py-2 text-sm">{{item.{f}}}</td>'
        for f in out_names
    )
    new_btn = (
        f'\n    {{#if canCreate}}\n'
        f'      <a href="/{schema_name}/{table_name}/new"\n'
        f'         class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm">\n'
        f'        New\n      </a>\n    {{/if}}'
        if has_post else ''
    )
    view_link = (
        f'\n            <a href="/{schema_name}/{table_name}/{{item.{pk_field}}}"\n'
        f'               class="text-blue-600 hover:underline text-sm">View</a>'
        if pk_field else ''
    )
    del_btn = (
        f'\n            {{#if canDelete}}\n'
        f'              <button onclick={{() => handleDelete(item.{pk_field})}}\n'
        f'                      class="text-red-600 hover:underline text-sm">Delete</button>\n'
        f'            {{/if}}'
        if has_del and pk_field else ''
    )
    delete_fn = (
        f'\n  async function handleDelete(id: string) {{\n'
        f'    if (confirm(\'Delete this item?\')) {{\n'
        f'      await {rname}Api.remove(id);\n'
        f'      {rname}State.items = {rname}State.items.filter(i => i.{pk_field} !== id);\n'
        f'    }}\n'
        f'  }}'
        if has_del and pk_field else ''
    )
    can_create = f"\n  const canCreate = $derived(!!access['{map_key}']?.POST);" if has_post else ''
    can_delete = f"\n  const canDelete  = $derived(!!access['{map_key}']?.DELETE);" if has_del else ''

    return f"""\
<script lang="ts">
  import {{ {rname}State, {rname}Api }} from '$lib/stores/{stem}.svelte.ts';
  import {{ auth }} from '$lib/auth.svelte.ts';
  import {{ hoAccess }} from '$lib/stores/index.svelte.ts';

  let access = $state<Record<string, any>>({{}});

  $effect(() => {{
    hoAccess(auth.token ?? undefined).then(a => {{ access = a; }});
    {rname}Api.list().then(r => r.json()).then(d => {{ {rname}State.items = d; }});
  }});
{can_create}{can_delete}{delete_fn}
</script>

<div>
  <div class="flex justify-between items-center mb-4">
    <h1 class="text-2xl font-bold">{title}</h1>{new_btn}
  </div>

  <div class="bg-white shadow-sm rounded-lg overflow-hidden">
    <table class="w-full border-collapse">
      <thead class="bg-gray-100">
        <tr>
        {th_cols}
          <th class="px-4 py-2"></th>
        </tr>
      </thead>
      <tbody>
        {{#each {rname}State.items as item}}
          <tr class="border-t hover:bg-gray-50">
          {td_cols}
            <td class="px-4 py-2 flex gap-3">{view_link}{del_btn}
            </td>
          </tr>
        {{/each}}
      </tbody>
    </table>
  </div>
</div>
"""


def _new_page(
    schema_name: str, table_name: str,
    stem: str, rname: str, iname: str,
    post_in_names: list, all_fields: dict,
) -> str:
    title = _title(schema_name, table_name)
    fields_init = ', '.join(f'{f}: ""' for f in post_in_names)
    form_fields = '\n    '.join(
        f'<div>\n'
        f'      <label class="block text-sm font-medium text-gray-700 mb-1">{f}</label>\n'
        f'      <input bind:value={{form.{f}}}\n'
        f'             class="w-full border rounded px-3 py-2 text-sm" />\n'
        f'    </div>'
        for f in post_in_names
    )
    return f"""\
<script lang="ts">
  import {{ {rname}Api }} from '$lib/stores/{stem}.svelte.ts';
  import type {{ {iname}PostIn }} from '$lib/stores/{stem}.svelte.ts';
  import {{ goto }} from '$app/navigation';

  let form = $state<{iname}PostIn>({{ {fields_init} }});
  let error = $state('');

  async function handleSubmit(e: Event) {{
    e.preventDefault();
    try {{
      const res = await {rname}Api.create(form);
      if (!res.ok) throw new Error(await res.text());
      goto('/{schema_name}/{table_name}');
    }} catch (err: any) {{
      error = err.message;
    }}
  }}
</script>

<div class="max-w-lg mx-auto p-6 bg-white rounded-lg shadow mt-6">
  <h1 class="text-2xl font-bold mb-6">New {title}</h1>
  {{#if error}}<p class="text-red-600 mb-4">{{error}}</p>{{/if}}
  <form onsubmit={{handleSubmit}} class="space-y-4">
    {form_fields}
    <div class="flex gap-3 pt-2">
      <button type="submit"
              class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm">
        Create
      </button>
      <a href="/{schema_name}/{table_name}"
         class="px-4 py-2 border rounded hover:bg-gray-50 text-sm">Cancel</a>
    </div>
  </form>
</div>
"""


def _detail_page(
    schema_name: str, table_name: str,
    stem: str, rname: str, iname: str,
    out_names: list, put_in_names: list,
    pk_field: str, all_fields: dict,
    has_put: bool,
) -> str:
    title = _title(schema_name, table_name)
    read_only = [f for f in out_names if f != pk_field and f not in put_in_names]

    ro_fields = '\n    '.join(
        f'<div class="flex gap-2 text-sm">'
        f'<span class="font-medium text-gray-600 w-32">{f}</span>'
        f'<span>{{item.{f}}}</span></div>'
        for f in read_only
    )

    fields_init = ', '.join(
        f'{f}: item.{f} ?? ""'
        for f in put_in_names
    )
    form_fields = '\n    '.join(
        f'<div>\n'
        f'      <label class="block text-sm font-medium text-gray-700 mb-1">{f}</label>\n'
        f'      <input bind:value={{form.{f}}}\n'
        f'             class="w-full border rounded px-3 py-2 text-sm" />\n'
        f'    </div>'
        for f in put_in_names
    ) if put_in_names else ''

    edit_section = ''
    if has_put and put_in_names:
        edit_section = f"""\

  <h2 class="text-lg font-semibold mt-6 mb-4">Edit</h2>
  {{#if error}}<p class="text-red-600 mb-4">{{error}}</p>{{/if}}
  <form onsubmit={{handleUpdate}} class="space-y-4">
    {form_fields}
    <div class="flex gap-3 pt-2">
      <button type="submit"
              class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm">
        Update
      </button>
      <a href="/{schema_name}/{table_name}"
         class="px-4 py-2 border rounded hover:bg-gray-50 text-sm">Cancel</a>
    </div>
  </form>"""

    update_fn = ''
    if has_put:
        update_fn = f"""\

  let form = $state({{ {fields_init} }});
  let error = $state('');

  async function handleUpdate(e: Event) {{
    e.preventDefault();
    try {{
      const res = await {rname}Api.update(data.id, form);
      if (!res.ok) throw new Error(await res.text());
      goto('/{schema_name}/{table_name}');
    }} catch (err: any) {{
      error = err.message;
    }}
  }}"""

    return f"""\
<script lang="ts">
  import {{ {rname}Api }} from '$lib/stores/{stem}.svelte.ts';
  import type {{ {iname}Out{', ' + iname + 'PutIn' if has_put else ''} }} from '$lib/stores/{stem}.svelte.ts';
  import {{ goto }} from '$app/navigation';
  import {{ page }} from '$app/state';

  let item = $state<{iname}Out | null>(null);

  $effect(() => {{
    {rname}Api.get(page.params.id).then(r => r.json()).then(d => {{ item = d; }});
  }});
{update_fn}
</script>

{{#if item}}
<div class="max-w-lg mx-auto p-6 bg-white rounded-lg shadow mt-6">
  <div class="flex justify-between items-start mb-6">
    <h1 class="text-2xl font-bold">{title}</h1>
    <a href="/{schema_name}/{table_name}" class="text-sm text-gray-500 hover:underline">← Back</a>
  </div>

  <div class="space-y-2 mb-4">
    <div class="flex gap-2 text-sm">
      <span class="font-medium text-gray-600 w-32">{pk_field}</span>
      <span class="font-mono text-xs">{{item.{pk_field}}}</span>
    </div>
    {ro_fields}
  </div>{edit_section}
</div>
{{/if}}
"""


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

class SvelteAppGenerator(StoreGenerator):

    def generate(self, classes, api_version, output_dir: Path) -> None:
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True)

        version_prefix = f'/v{api_version}' if api_version is not None else ''
        project_name = output_dir.name

        # --- static files ---
        self._write(output_dir / 'package.json',
                    _PACKAGE_JSON.format(project_name=project_name))
        self._write(output_dir / 'svelte.config.js',    _SVELTE_CONFIG)
        self._write(output_dir / 'vite.config.ts',
                    _VITE_CONFIG.format(version_prefix=version_prefix or '/api'))
        self._write(output_dir / 'tsconfig.json',        _TSCONFIG)
        self._write(output_dir / 'tailwind.config.js',  _TAILWIND_CONFIG)
        self._write(output_dir / 'postcss.config.js',   _POSTCSS_CONFIG)
        self._write(output_dir / 'src' / 'app.html',    _APP_HTML)
        self._write(output_dir / 'src' / 'app.css',     _APP_CSS)

        # --- stores (reuse SvelteGenerator) ---
        stores_dir = output_dir / 'src' / 'lib' / 'stores'
        SvelteGenerator().generate(classes, api_version, stores_dir)

        # --- auth store ---
        self._write(output_dir / 'src' / 'lib' / 'auth.svelte.ts', _AUTH_STORE)

        # --- collect resources ---
        resources = []
        for relation, _relation_type in classes:
            module_str = relation.__module__
            try:
                mod = importlib.import_module(module_str)
            except ImportError:
                continue
            if not getattr(mod, 'CRUD_ACCESS', None):
                continue
            crud_access  = mod.CRUD_ACCESS
            api_excluded = getattr(mod, 'API_EXCLUDED_FIELDS', [])
            schema_name  = relation._schemaname.replace('.', '_')
            table_name   = relation.__name__.lower()
            inst         = _instance(relation)
            all_fields   = getattr(inst, '_ho_fields', {})
            all_names    = list(all_fields.keys())
            pk_info      = _simple_pk(relation)
            pk_field     = pk_info[0] if pk_info else None
            iname        = self.interface_name(schema_name, table_name)
            rname        = self.resource_name(schema_name, table_name)
            stem         = f'{schema_name}_{table_name}'
            map_key      = f'{schema_name}/{table_name}'

            out_names = _gen_out_fields(crud_access, 'GET', api_excluded, all_names)
            if not out_names:
                out_names = [f for f in all_names if f not in api_excluded]

            has_post = 'POST' in crud_access and bool(pk_info)
            has_put  = 'PUT'  in crud_access and bool(pk_info)
            has_del  = 'DELETE' in crud_access and bool(pk_info)

            post_in_names = _gen_in_fields(
                crud_access, 'POST', pk_field, api_excluded, all_names
            ) if has_post else []
            put_in_names = _gen_in_fields(
                crud_access, 'PUT', pk_field, api_excluded, all_names
            ) if has_put else []

            resources.append((
                schema_name, table_name, stem, rname, iname,
                out_names, pk_info, pk_field, all_fields,
                has_post, has_put, has_del,
                post_in_names, put_in_names, map_key, crud_access,
            ))

        # --- layout + home ---
        routes_dir = output_dir / 'src' / 'routes'
        self._write(routes_dir / '+layout.svelte',
                    _layout(resources))
        first_route = (
            f'/{resources[0][0]}/{resources[0][1]}' if resources else '/'
        )
        self._write(routes_dir / '+page.svelte',
                    _HOME_PAGE.format(first_route=first_route))
        self._write(routes_dir / 'login' / '+page.svelte', _LOGIN_PAGE)

        # --- per-resource routes ---
        for (schema_name, table_name, stem, rname, iname,
             out_names, pk_info, pk_field, all_fields,
             has_post, has_put, has_del,
             post_in_names, put_in_names, map_key, crud_access) in resources:

            res_dir = routes_dir / schema_name / table_name

            # list
            self._write(
                res_dir / '+page.svelte',
                _list_page(schema_name, table_name, stem, rname, iname,
                           out_names, pk_info, has_post, has_del, map_key),
            )

            # new (POST)
            if has_post:
                self._write(
                    res_dir / 'new' / '+page.svelte',
                    _new_page(schema_name, table_name, stem, rname, iname,
                              post_in_names, all_fields),
                )

            # detail (GET by pk)
            if pk_info and 'GET' in crud_access:
                self._write(
                    res_dir / '[id]' / '+page.svelte',
                    _detail_page(schema_name, table_name, stem, rname, iname,
                                 out_names, put_in_names, pk_field, all_fields,
                                 has_put),
                )

        print(f'\nSvelteKit app generated in {output_dir}')
        print('Next steps:')
        print(f'  cd {output_dir}')
        print('  npm install')
        print('  npm run dev')

    def _write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        print(f'  {path}')
