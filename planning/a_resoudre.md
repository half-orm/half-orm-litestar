# À résoudre

## ~~1. Rôles dynamiques — frontend Svelte~~ ✓

Terminé :
- `resource.silo.svelte.ts` : signal `dynamicRoles`, méthode `canUpdate(id)`, `refresh()` via endpoint liste pour récupérer `meta.dynamic_roles`, reset systématique.
- `svelte.py` : page detail `canEdit || canUpdate(id)`, page access lecture seule (plus de `selectRole`/`auth.login(role)`), `_auth_store` JWT complet, `_layout` trois états.

## ~~2. Champs FK résolus automatiquement dans les formulaires~~ ✓

Implémenté via `fk_auto` : table `field_access_fk_auto`, trois types (`connected_user`, `context`, `select`), admin UI Angular, silo signals, runtime injection backend, embedded list New button.

## ~~3. Matrice des permissions — refonte~~ ✓

Réalisé : `<PermissionsMatrix>` supprimée des pages list/detail, matrice réservée à l'admin Angular alimentée par `/ho_admin/catalog`, simulation de rôle (`simulateRole` / `exitSimulation`) avec bannière.

## 4. Champs avec valeur par défaut marqués « auto » à tort dans les formulaires PUT

`_is_server_generated` traite comme auto tout champ ayant une valeur par défaut DB (ex. `published DEFAULT false`), ce qui les exclut des formulaires d'édition. Ce traitement doit être réservé aux clefs primaires et aux champs générés par le serveur (séquences, `DEFAULT gen_random_uuid()`, etc.). Les champs avec une simple valeur par défaut doivent rester éditables.

## ~~5. Admin — droits d'accès hérités par le parent~~ ✓

`openPanel` auto-crée l'own entry si hérité, `hasAncestorVerb` verrouille la checkbox même après création, warning supprimé sur verbe couvert par un ancêtre.

## 6. Rôles dynamiques — résolution systématique pour tous les verbes

Le mécanisme de résolution dynamique des rôles n'est actuellement implémenté que pour GET (liste, affichage `meta.dynamic_roles`) et PUT (handler backend + bouton Edit frontend). Il faut l'étendre à tous les verbes de façon cohérente.

**Cas concret** : si `post_author` a DELETE → pas de bouton Delete pour Alice. Si on voulait n'autoriser POST sur `blog/comment` qu'au propriétaire du post → le bouton Create n'apparaîtrait pas et le handler POST ne validerait pas le rôle dynamique.

**Ce qui manque par verbe :**
- DELETE : `canDeleteRow(id)` côté silo + condition dans les templates list + handler DELETE backend
- POST : `canCreateInContext(parentId?)` côté silo + condition sur le bouton Create + handler POST backend
- GET (filtre) : envisager de filtrer les lignes retournées selon le rôle dynamique (ex. n'afficher que ses propres posts)

**Approche** : généraliser le pattern `canUpdate` → `canActionRow(verb, id)`, et côté backend appliquer la résolution dynamique dans tous les handlers (POST, PUT, DELETE) avant le contrôle d'accès.

## 7. Champ « searchable » par field — composant de recherche universel

Ajouter un flag `searchable` par champ **par accès/rôle** dans l'interface Admin. Ce flag indique quels champs peuvent être utilisés pour filtrer/rechercher les enregistrements d'une ressource via `?q=...`.

**Usage 1 — select FK** : pour les champs FK de type `select` dans les formulaires Create, peupler le combobox en recherchant sur les champs `searchable` de la ressource cible. Sans ce flag, on doit charger toutes les lignes (non scalable).

**Usage 2 — recherche universelle sur les listes** : n'importe quelle vue liste peut exposer une barre de recherche dès qu'au moins un champ est marqué `searchable`. Le flag contrôle aussi **qui peut chercher quoi** : un rôle peut avoir GET sur une ressource mais être limité à zéro champ searchable (liste possible, recherche interdite), ou avoir accès à un sous-ensemble de champs filtrables.

**Niveau de stockage** : par accès/rôle (comme `field_access_in`/`field_access_out`), pas global par ressource — ce qui permet la granularité par rôle.

**À propager** : dans le catalog `/ho_admin/catalog`, dans `/ho_access` (par verb GET), et dans les silos frontend (`searchableFields` signal).

## 8. Scaffold de composants personnalisés — `half_orm gen frontend --list|--edit|--display <schema.table>`

Ajouter des sous-commandes de scaffold pour générer un composant unique sans régénérer tout le frontend :

```bash
half_orm gen frontend --angular --list blog.post      # liste filtrée standalone
half_orm gen frontend --angular --edit blog.post      # formulaire d'édition seul
half_orm gen frontend --angular --display blog.post   # vue lecture seule
```

**Cas d'usage** : intégrer une liste filtrée de `blog.post` dans une page applicative existante (hors backoffice généré), ou générer un composant de sélection pour un FK `select`.

**Ce que ça génère** : le composant Angular/Svelte correspondant (fichier `.ts` + `.html` ou `.svelte`), pré-câblé sur le silo de la ressource, avec les guards d'accès. Le fichier est placé dans un répertoire `custom/` pour ne pas être écrasé par un `gen frontend` complet.

**Lien avec searchable** : le composant `--list` pourrait intégrer automatiquement la barre de recherche si des champs `searchable` sont configurés.
