# Creating a Calibre-Web theme

This guide explains how to build a theme for Calibre-Web: from a single stylesheet that restyles the
standard look, to a theme that replaces parts of the HTML.

- [How theming works](#how-theming-works)
- [Quick start: a CSS-only theme](#quick-start-a-css-only-theme)
- [Installing a theme](#installing-a-theme)
- [`info.json` reference](#infojson-reference)
- [Static files](#static-files)
- [Styling hooks](#styling-hooks)
- [Parent themes](#parent-themes)
- [Overriding templates](#overriding-templates)
- [Layout blocks](#layout-blocks)
- [What a theme cannot change](#what-a-theme-cannot-change)
- [Testing and troubleshooting](#testing-and-troubleshooting)

## How theming works

Every page is built from three layers:

| Layer | What it contains | Who provides it |
|---|---|---|
| **Framework** | Bootstrap 5 (CSS + JS), Bootstrap Icons | Always loaded |
| **Base** | The standard HTML templates and `css/style.css` | Always loaded, shared by every theme |
| **Look** | The theme's own CSS, JavaScript, fonts, images and (optionally) templates | Your theme |

The bundled *Standard* theme is itself just a look on top of the base: it adds `standard.css` and
`standard.js`. The bundled *caliBlur!* theme adds its own CSS and JavaScript and replaces a number of templates.

A theme is a folder:

```
mytheme/
  info.json          required: name, identifier, settings
  static/            optional: CSS, JavaScript, fonts, images
  templates/         optional: HTML templates that replace the standard ones
```

You can build three kinds of theme with it:

1. **A restyle of Standard** — `"parent": "standard"` plus one stylesheet. Smallest, easiest to keep working.
2. **A blank-canvas theme** — no parent; you style the base markup from scratch.
3. **A theme that changes markup** — one of the above plus templates in `templates/`. Most powerful, most maintenance.

Prefer the first two. Every template you copy is a template you have to update when Calibre-Web changes it.

## Quick start: a CSS-only theme

This creates a "Sepia" theme that keeps the standard layout and changes the colours.

1. Find the folder that contains Calibre-Web's settings database (`app.db`) and create `themes/sepia/` next to it.
   (With Docker this is usually your mounted `/config` folder.)

2. Create `themes/sepia/info.json`:

   ```json
   {
     "name": "Sepia",
     "identifier": "sepia",
     "application": "cps",
     "author": "Your Name",
     "description": "Warm paper colours on top of the Standard theme",
     "version": "1.0",
     "options": {
       "parent": "standard",
       "css_files": ["css/sepia.css"],
       "body_class": "sepia"
     }
   }
   ```

3. Create `themes/sepia/static/css/sepia.css`:

   ```css
   body.sepia {
     --bs-body-bg: #f4ecd8;
     --bs-body-color: #3b2f22;
     background-color: var(--bs-body-bg);
   }

   body.sepia .navbar {
     background-color: #e8dcc0 !important;
   }

   body.sepia .sidebar-column {
     background-color: #efe4ca;
   }
   ```

4. Restart Calibre-Web.

5. Go to **Admin → Edit UI Configuration → Theme**, choose **Sepia** and save.

Scoping every rule under `body.sepia` (the `body_class` from `info.json`) keeps your styles from leaking and makes
them win over the standard rules without `!important` in most cases.

## Installing a theme

Calibre-Web loads themes from two places:

| Location | Contents |
|---|---|
| `cps/themes/` inside the application | The bundled `standard` and `caliblur` themes. Do not put your own themes here: updates replace this folder. |
| `themes/` next to `app.db`, or the folder in `CALIBRE_THEMES_DIR` | Your themes. |

The settings database is wherever you pointed Calibre-Web with `-p` or `CALIBRE_DBPATH`; without either, it is the
Calibre-Web folder itself (or `~/.calibre-web` for a pip installation). The log shows the folder that is used:

```
INFO {themes.py} Loading user themes from /config/themes
```

To install a theme, copy its folder (unzipped) into that `themes/` folder and restart Calibre-Web.

> **Only install themes from sources you trust.** A theme is code, not just styling: its templates are Jinja
> templates that run unsandboxed on the server with access to the application, and its JavaScript runs in the
> browser of every user, including administrators. Read a theme's `templates/` and JavaScript before installing it.

**Docker.** If the config folder is already a volume (for example `./config:/config` with the
linuxserver.io image), put themes in `./config/themes/`. You can also mount a separate folder, read-only is fine:

```yaml
services:
  calibre-web:
    image: lscr.io/linuxserver/calibre-web
    volumes:
      - ./config:/config
      - ./my-themes:/config/themes:ro
```

or point to any folder with an environment variable:

```yaml
    environment:
      - CALIBRE_THEMES_DIR=/themes
    volumes:
      - ./my-themes:/themes:ro
```

Rules that apply to every installed theme:

- The folder name must be exactly the theme's `identifier`.
- Identifiers may only contain letters, digits and underscores, and must not start with a digit (`my_theme`, not `my-theme`).
- A theme cannot replace a bundled theme: a folder called `standard` or `caliblur` is skipped.
- Changes are picked up on restart.

If a theme is skipped, the log says which folder and why.

## `info.json` reference

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | Name shown in the theme dropdown. |
| `identifier` | yes | Unique id; must equal the folder name. Stored in the settings when the theme is selected. |
| `application` | yes | Always `"cps"`. Any other value makes Calibre-Web ignore the theme without a log message. |
| `author` | yes | Your name. |
| `description` | no | Short description. |
| `version` | no | Your theme's version. |
| `license`, `license_url`, `website` | no | Informational. |
| `options.parent` | no | Identifier of a theme to build on. See [Parent themes](#parent-themes). |
| `options.css_files` | no | Stylesheets to load, relative to `static/`, in order. |
| `options.js_files` | no | Scripts to load, relative to `static/`, in order. |
| `options.body_class` | no | Class(es) added to `<body>` on every page while the theme is active. |

## Static files

Everything in `static/` is served at `/_themes/<identifier>/<path>`. With the example above,
`static/css/sepia.css` is served as `/_themes/sepia/css/sepia.css` (prefixed automatically when Calibre-Web runs
under a sub-path behind a reverse proxy).

- **Stylesheets** listed in `css_files` are loaded after Bootstrap, `style.css`, the upload styles, Bootstrap Icons
  and the parent theme's stylesheets, so your rules win when specificity is equal.
- **Scripts** listed in `js_files` are loaded after jQuery, Bootstrap, the Calibre-Web scripts (`main.js`) and the
  parent theme's scripts, at the end of `<body>`.
- **Fonts and images**: reference them from your CSS with relative URLs; they resolve against the CSS file.

  ```css
  @font-face {
    font-family: "Literata";
    src: url("../fonts/Literata.woff2") format("woff2");   /* static/fonts/Literata.woff2 */
  }
  body.sepia { background-image: url("../img/paper.png"); }  /* static/img/paper.png */
  ```

- **From a template**, use `theme_static('img/logo.svg')` to get the URL of a file: it comes from the active theme,
  or from the first parent theme that has the file.

Calibre-Web's Content Security Policy only allows fonts from its own address, and scripts and stylesheets only from
its own address plus the hosts an admin lists as trusted. Host fonts, scripts and stylesheets inside your theme instead
of linking to a CDN.

## Styling hooks

Things you can rely on in CSS:

- **`<body>` classes**: the current page name, plus your theme's `body_class` (and those of its parents).
  Page names include `newest` (book list home page), `book`, `search`, `advsearch`, `discover`, `hot`, `rated`,
  `author`, `authorlist`, `series`, `serieslist`, `category`, `catlist`, `publisher`, `language`, `shelf`, `me`,
  `login`, `register`, `stat`, `tasks`, `admin`, `config`, `uiconfig`, `dbconfig`, `mailset`, `usertable`,
  `edituser`, `newuser`, `editbook`, `logfile`.
- **Page regions**: `nav.navbar` (top bar), `#main-nav` (right-hand navbar items), `.sidebar-column` and
  `#scnd-nav` (sidebar), `.page-content` (main column), `#bookDetailsModal` (book details pop-up).
- **Bootstrap 5 CSS variables** (`--bs-body-bg`, `--bs-body-color`, `--bs-primary`, …) for broad colour changes.

Class names on individual elements can change between Calibre-Web versions. Prefer the hooks above, IDs, and
Bootstrap variables over long selectors that depend on exact nesting.

## Parent themes

`options.parent` names another theme (bundled or installed) to build on. Calibre-Web then:

- loads the parent's `css_files` and `js_files` before yours;
- adds the parent's `body_class` before yours;
- uses the parent's templates for anything your theme does not provide, before falling back to standard.

Chains work too (`a` → `b` → `standard`). An unknown parent, or a theme that ends up being its own ancestor, stops
the chain at that point and logs a warning.

**Without a parent** you get the base layer only: Bootstrap, `style.css`, the standard HTML. That is the cleanest
starting point for a completely different look, with one consequence: `standard.js`, which moves the sidebar into the
top bar on narrow screens, is part of the Standard look. Either set `"parent": "standard"`, or handle the
`#scnd-nav` sidebar on small screens in your own CSS or JavaScript.

## Overriding templates

Put a file with the same name as a standard template in your theme's `templates/` folder and it is used instead.
Anything you do not provide comes from your parent theme, and then from the standard theme. The standard templates are
in `cps/themes/standard/templates/` of the Calibre-Web source:

```
admin.html  author.html  book_edit.html  book_exists_flash.html  book_table.html  config_db.html
config_edit.html  config_view_edit.html  detail.html  email_edit.html  generate_kobo_auth_url.html  grid.html
http_error.html  index.html  layout.html  list.html  listenmp3.html  login.html  logviewer.html
modal_dialogs.html  read.html  readcbr.html  readdjvu.html  readpdf.html  readtxt.html  register.html
remote_login.html  remote_login_verify.html  schedule_edit.html  search.html  search_form.html  shelf.html
shelf_edit.html  shelf_order.html  shelfdown.html  stats.html  tasks.html  user_edit.html  user_table.html
```

**Do not copy whole files if you can avoid it.** Extend the standard template and replace only the
[blocks](#layout-blocks) you need:

```jinja
{# mytheme/templates/layout.html #}
{% extends "_themes/standard/layout.html" %}

{% block nav_after_header %}
  <a class="home-button" href="{{ url_for('web.index') }}" title="{{ _('Home') }}"></a>
{% endblock %}

{% block nav_search %}
  {{ super() }}                       {# keep the standard search form, add something after it #}
  <span class="search-hint">{{ _('Search Library') }}</span>
{% endblock %}
```

- `{{ super() }}` renders the standard content of the block, so you can add to it instead of replacing it.
- Other pages extend `theme("layout.html")`, so they automatically use your layout.
- The same works for any page: `{% extends "_themes/standard/config_edit.html" %}` and override its blocks.
- Use `_('…')` for every visible text so it is translated; reuse texts that already exist in Calibre-Web where you
  can, because new texts have no translations.

Templates have access to the same variables as the standard ones, among others `current_user`, `g.theme` (the
selected theme; not set on some early error pages), `page`, `title`, `url_for`, `theme_static(path)`, `theme_assets('css_files' | 'js_files')` and
`theme_body_class()`.

A template-overriding theme is tied to the Calibre-Web version it was written for. When upgrading, compare your
templates with the new standard ones.

## Layout blocks

`layout.html` (the frame around every regular page) has these blocks. The default content of each block is the
standard markup.

| Block | Where | Default |
|---|---|---|
| `header` | inside `<head>`, before `style.css` | empty (pages add their CSS here) |
| `body_class` | extra classes on `<body>` | empty |
| `body_attrs` | extra attributes on `<body>` | empty |
| `navbar_class` | `class` of the top `<nav>` | Bootstrap navbar classes |
| `nav_header` | brand name and menu toggle button | standard brand + toggler |
| `nav_after_header` | right after the brand | empty |
| `nav_search` | quick search form | standard search form |
| `nav_links` | left-hand navbar links | Advanced Search, Simple Theme |
| `main_nav_class` | `class` of `#main-nav` | Bootstrap nav classes |
| `nav_main_start` | first item in `#main-nav` | empty |
| `nav_upload` | upload button | standard upload form |
| `nav_tasks` | Tasks link | standard link |
| `nav_admin` | Admin link | standard link |
| `nav_user` | profile and logout links | standard links |
| `nav_guest` | login and register links (anonymous users) | standard links |
| `nav_after_collapse` | end of the navbar | empty |
| `flash_messages` | success/error messages | standard alerts |
| `flash` | after the messages (pages add spinners here) | empty |
| `before_content` | between the navbar and the page | empty |
| `content_row_class` | `class` of the main row | `row row-fluid` |
| `sidebar_column_class` | `class` of the sidebar column | `col-md-2 sidebar-column d-none d-md-block` |
| `scnd_nav_attrs` | extra attributes on `#scnd-nav` | empty |
| `nav_head_class` | visibility class of sidebar headings | `d-md-block` |
| `sidebar_top` | top of the sidebar, after "Browse" | empty |
| `sidebar_item` | one sidebar entry (variable `element`) | standard entry |
| `sidebar_shelf_item` | one shelf entry (variable `shelf`) | standard entry |
| `sidebar_about` | "About" link in the sidebar | standard link |
| `content_column_class` | `class` of the main column | `col-12 col-md-10 page-content` |
| `body` | the page itself | filled by each page |
| `details_modal_title` | title of the book details pop-up | `<h5>` title |
| `modal` | extra dialogs | filled by pages |
| `vendor_js` | scripts that must load before Calibre-Web's plugins | empty |
| `js` | page scripts | filled by pages |

Blocks on the settings pages (`config_edit.html`, `config_view_edit.html`): `config_accordion_class` and
`config_actions_class`.

The bundled caliBlur theme's `templates/layout.html` is a complete example of a layout built from these blocks.

## What a theme cannot change

- **Shared templates** in `cps/templates/`: the cover image macro (`image.html`), the OPDS catalogue feeds and a few
  fragments. They are not looked up per theme.
- **The simple e-reader view** (`/basic`, offered to Kindle, Kobo, Tolino and Bookeen browsers) always uses the
  standard theme.
- **The book readers** (`read.html`, `readpdf.html`, `readcbr.html`, …) are complete pages that do not load your
  `css_files`. To restyle a reader, override its template.
- **The reading colours inside the epub reader** (Light, Dark, Sepia, …) are a per-user reader setting, separate from
  the site theme.

## Testing and troubleshooting

Check your theme on at least: the book list, a book's detail page and pop-up, search, your profile, the admin
pages, the login page (log out first) and an error page (open a URL that does not exist). Check a narrow window
(phone width) as well as a wide one.

| Problem | Cause and fix |
|---|---|
| Theme not in the dropdown | Look for `Theme folder '…' skipped` in the log: invalid `info.json`, a value of the wrong type, folder name different from `identifier`, a `-` in the name, or the name of a bundled theme. A theme whose `application` is not `"cps"` is dropped **without** a log line, so check that field too. Restart after fixing. |
| Theme in the dropdown, styles not applied | Check the browser's network panel for 404s: paths in `css_files` are relative to `static/`. Check that your selectors use your `body_class`. |
| Changes not visible | Restart Calibre-Web after changing `info.json` or templates; force-reload the browser for CSS and JS changes. |
| Page looks like Standard after an upgrade | Your selected theme folder is missing; the log says `Theme '…' not found, using 'standard'`. |
| Sidebar does not collapse into the top bar on phones | Your theme has no parent; see [Parent themes](#parent-themes). |
| Error after an upgrade on one page | A template you copied no longer matches what the page passes in. Compare it with the new standard template, or delete your copy to fall back to standard. |

For developers working on Calibre-Web itself: `tests/snapshot_pages.sh` saves the HTML of the main pages so you can
diff a theme or template change before and after. Run it twice against a copy of `app.db`, with `CW_USER`/`CW_PASS`
set, and compare with `diff -r -I csrf_token before/ after/`.
