# Plan : `half_orm litestar gen-frontend --svelte`

## Contexte

`gen-store --svelte` génère des stores Svelte 5 typés depuis `CRUD_ACCESS`.
L'étape suivante est de scaffolder une application SvelteKit complète et
jetable (POC) : listes, formulaires, nav, auth JWT minimale. Le scaffold est
généré une seule fois et n'est jamais regénéré — le développeur le modifie
ensuite librement.

---

## Commande CLI

```
half_orm litestar gen-frontend --svelte [--output frontend/svelte]
```

- Remplace fonctionnellement `gen-store` (les stores sont inclus dans l'app)
- `gen-store` reste disponible pour le cas "stores seuls"
- `--output` : défaut `frontend/svelte`
- Extensible : `--ngrx`, `--pinia` à venir

---

## Architecture

### Nouveaux fichiers Python

```
half_orm_litestar/gen_app/
├── __init__.py      ← GenApp orchestrateur
└── svelte.py        ← SvelteAppGenerator (templates inline)
```

`cli_extension.py` : ajout de la commande `gen-frontend`.

### Sortie générée (blog_demo)

```
frontend/svelte/
├── package.json
├── svelte.config.js
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.js
├── postcss.config.js
├── src/
│   ├── app.html
│   ├── app.css              ← directives Tailwind
│   ├── lib/
│   │   ├── auth.svelte.ts   ← token $state + login/logout
│   │   └── stores/          ← SvelteGenerator (réutilisé)
│   │       ├── blog_author.svelte.ts
│   │       ├── blog_post.svelte.ts
│   │       └── index.svelte.ts
│   └── routes/
│       ├── +layout.svelte   ← nav générée depuis les ressources
│       ├── +page.svelte     ← accueil (redirect vers première ressource)
│       ├── login/
│       │   └── +page.svelte ← saisie token JWT
│       └── {schema}/
│           └── {table}/
│               ├── +page.svelte       ← liste + filtres
│               ├── new/
│               │   └── +page.svelte   ← formulaire création (si POST)
│               └── [id]/
│                   └── +page.svelte   ← détail + édition (si GET+PUT)
```

---

## Réutilisation

`SvelteGenerator` (`gen_store/svelte.py`) est appelé directement par
`SvelteAppGenerator` pour produire `src/lib/stores/`. Aucune duplication.

---

## Fichiers statiques (templates fixes)

Contenus inline dans `gen_app/svelte.py` :

| Fichier | Contenu |
|---------|---------|
| `package.json` | SvelteKit, Vite, Tailwind, svelte-check, TypeScript |
| `svelte.config.js` | adapter-auto, vitePreprocess |
| `vite.config.ts` | plugin sveltekit() |
| `tsconfig.json` | extends .svelte-kit/tsconfig.json |
| `tailwind.config.js` | content: src/**/*.{svelte,ts} |
| `postcss.config.js` | tailwindcss + autoprefixer |
| `src/app.html` | <!doctype html> minimal |
| `src/app.css` | @tailwind base/components/utilities |

---

## auth.svelte.ts (généré)

```typescript
export let token = $state<string | null>(sessionStorage.getItem('ho_token'));

export function login(t: string) {
    sessionStorage.setItem('ho_token', t);
    token = t;
}
export function logout() {
    sessionStorage.removeItem('ho_token');
    token = null;
}
```

---

## login/+page.svelte (généré)

Formulaire simple : champ textarea pour coller un token JWT → appel `login()`
→ redirect vers `/`.

---

## +layout.svelte (généré depuis les ressources)

```svelte
<script>
  import { token, logout } from '$lib/auth.svelte.ts';
</script>
<nav class="...">
  <a href="/blog/author">Authors</a>
  <a href="/blog/post">Posts</a>
  ...
  {#if token}
    <button onclick={logout}>Logout</button>
  {:else}
    <a href="/login">Login</a>
  {/if}
</nav>
<slot />
```

---

## Liste +page.svelte (pattern par ressource)

```svelte
<script>
  import { blogAuthorState, blogAuthorApi } from '$lib/stores/blog_author.svelte.ts';
  import { token } from '$lib/auth.svelte.ts';
  import { hoAccess } from '$lib/stores/index.svelte.ts';

  let access = $state<Record<string, any>>({});

  $effect(() => {
    hoAccess(token ?? undefined).then(a => { access = a; });
    blogAuthorApi.list().then(r => r.json()).then(d => { blogAuthorState.items = d; });
  });

  const canCreate = $derived(!!access['blog/author']?.POST);
  const canDelete = $derived(!!access['blog/author']?.DELETE);
</script>

<div class="p-4">
  <div class="flex justify-between mb-4">
    <h1 class="text-2xl font-bold">Authors</h1>
    {#if canCreate}<a href="/blog/author/new" class="btn">New</a>{/if}
  </div>
  <table class="w-full border-collapse">
    <thead><tr>{/* colonnes Out */}</tr></thead>
    <tbody>
      {#each blogAuthorState.items as item}
        <tr>
          {/* cellules */}
          <td>
            <a href="/blog/author/{item.id}">View</a>
            {#if canDelete}
              <button onclick={() => blogAuthorApi.remove(item.id)}>Delete</button>
            {/if}
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
</div>
```

---

## Formulaire new/+page.svelte (si POST)

Champs depuis `PostIn` interface. Submit → `blogAuthorApi.create(data)`
→ redirect vers la liste.

## Détail [id]/+page.svelte (si GET + PUT)

Charge l'item via `blogAuthorApi.get(id)`, affiche les champs `Out`,
formulaire d'édition avec les champs `PutIn`, submit → `blogAuthorApi.update(id, data)`.

---

## GenApp orchestrateur

```python
class GenApp:
    def __init__(self, repo, *, generator, output_dir, api_version):
        self._classes = list(repo.model.classes())
        generator.generate(self._classes, api_version, output_dir)
```

`SvelteAppGenerator.generate()` :
1. Nettoie `output_dir` (comme SvelteGenerator)
2. Écrit les fichiers statiques
3. Appelle `SvelteGenerator.generate(classes, api_version, output_dir / 'src/lib/stores')`
4. Génère `src/lib/auth.svelte.ts`
5. Génère `src/routes/+layout.svelte` et `+page.svelte`
6. Génère `src/routes/login/+page.svelte`
7. Pour chaque ressource : génère list / new / [id] pages

---

## cli_extension.py

```python
@litestar.command('gen-frontend')
@click.option('--svelte', 'framework', flag_value='svelte', default=True)
@click.option('--output', default=None)
def gen_frontend(framework, output):
    """Generate a throwaway SvelteKit POC from CRUD_ACCESS."""
    ...
    from half_orm_litestar.gen_app.svelte import SvelteAppGenerator
    output_dir = Path(output) if output else Path('frontend') / framework
    GenApp(repo, generator=SvelteAppGenerator(),
           output_dir=output_dir, api_version=api_version)
```

---

## Vérification

```bash
cd blog_demo
half_orm litestar gen-frontend --svelte
cd frontend/svelte
npm install
npm run dev
# → http://localhost:5173
# Vérifier : nav présente, liste authors visible, login redirige,
#            hoAccess filtre les boutons selon le token
```
