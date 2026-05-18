# Branding Abstraction

This document tracks the effort to make dandi-archive re-brandable (white-label
capable) so that the same codebase can be deployed under different instance names,
URLs, logos, and visual identities without forking.

Related issue: https://github.com/dandi/dandi-archive/issues/2762

## Current State

### Existing multi-instance support

The codebase already has partial support via `dandischema`'s `instance_config`:

- **Backend settings** (`dandiapi/settings/base.py`):
  `DANDI_INSTANCE_NAME`, `DANDI_INSTANCE_IDENTIFIER`, `DANDI_WEB_APP_URL`,
  `DANDI_API_URL`, `DANDI_JUPYTERHUB_URL` — all env-var configurable.

- **API endpoint** (`/api/info/`): Serves `instance_config` from `dandischema`
  (instance_name, instance_identifier, instance_url, doi_prefix, licenses).

- **Frontend store** (`web/src/stores/instance.ts`): Pinia store that fetches
  instance config at startup; components can use `instanceName`,
  `instanceIdentifier`, `instanceUrl`.

- **[PR #2765](https://github.com/dandi/dandi-archive/pull/2765)** (`bf-2762`
  branch): Addresses the vendorization aspect — makes `instanceName` and
  `instanceIdentifier` dynamic wherever they appear in user-visible output.
  This covers citation formats (`cff.ts`), `HowToCiteTab.vue`,
  `DandisetList.vue`, `directives/index.ts`, `DownloadDialog.vue`, and e2e
  tests. These use the existing `instance_config` from `/api/info/` and do
  **not** require additional branding templating — they already work correctly
  for any instance (DANDI, EMBER, etc.) as long as the backend env vars
  `DANDI_INSTANCE_NAME` and `DANDI_INSTANCE_IDENTIFIER` are set.
  Also adds `scripts/check-no-hardcoded-dandi.sh` lint guard + pre-commit hook.

### What remains hardcoded

All remaining hardcoded branding touchpoints are annotated with `TODO: BRANDING`
comments (see [Annotation Conventions](#annotation-conventions) below).

## Annotation Conventions

Every location where instance-specific branding is hardcoded is marked with
`TODO: BRANDING` comments. This makes it trivial to find all branding points:

```bash
git grep -rn "TODO: BRANDING"
```

### Marker format

The marker format is the same regardless of source language — only the
surrounding comment syntax differs:

| Scope | Marker |
|-------|--------|
| Single line — name only (Group 1) | `TODO: BRANDING(name)` with optional `- description` |
| Single line — needs new config (Group 2) | `TODO: BRANDING` with optional `- description` |
| Multi-line block start | `TODO: BRANDING START` with optional `- description` |
| Multi-line block end | `TODO: BRANDING END` |

Group 1 items tagged `BRANDING(name)` can be resolved using existing
vendorization variables (`settings.DANDI_INSTANCE_NAME` / `instanceStore.instanceName`).
Group 2 items tagged plain `BRANDING` require new branding configuration.

Examples by file type:

```python
# TODO: BRANDING - hardcoded archive name in email subject
subject=f'DANDI: New user registered: {user.email}',
```

```python
# TODO: BRANDING START - hardcoded site domain and name
defaults={
    'domain': 'api.dandiarchive.org',
    'name': 'DANDI Archive',
},
# TODO: BRANDING END
```

```typescript
// TODO: BRANDING START - hardcoded instance-specific URLs
const dandiUrl = 'https://dandiarchive.org';
// ...
// TODO: BRANDING END
```

```html
<!-- TODO: BRANDING - hardcoded archive title -->
<title>DANDI Archive</title>
```

```html
<!-- TODO: BRANDING START - hardcoded archive name and tagline -->
<div>The DANDI Archive</div>
<div>The BRAIN Initiative archive...</div>
<!-- TODO: BRANDING END -->
```

```django
{# TODO: BRANDING - hardcoded archive name #}
```

## Annotated Inventory

Annotations are split into two groups:

- **Group 1 — Instance name substitution** (`TODO: BRANDING(name)`): Can be
  fixed now using existing vendorization variables
  (`settings.DANDI_INSTANCE_NAME` on backend,
  `instanceStore.instanceName` on frontend). These are pure "DANDI" →
  `instanceName` replacements.

- **Group 2 — Custom branding config needed** (`TODO: BRANDING`): Requires
  new configuration mechanism (images, URLs, colors, custom text blocks,
  funding info). These cannot be derived from `instanceName` alone.

Some locations contain both — the instance name part (Group 1) and
custom URLs/text (Group 2). These are listed in Group 2 with the Group 1
portion noted.

To find only Group 1 items: `git grep "BRANDING(name)"`
To find all branding items: `git grep "TODO: BRANDING"`

### Group 1 — Instance name substitution (can use existing vars)

Frontend — use `instanceStore.instanceName`:

| File | What to replace |
|------|-----------------|
| `web/index.html` | Page `<title>` ("DANDI Archive" → `instanceName + " Archive"`) |
| `web/index.html` | Noscript message ("DANDI Archive") |
| `web/src/components/CookieBanner.vue` | "best experience on DANDI" |
| `web/src/views/HomeView/StatsBar.vue` | "A DANDI dataset" description |
| `web/src/views/CreateDandisetView/CreateDandisetView.vue` | "DANDI only supports 5 years of embargo" |
| `web/src/components/FileBrowser/FileUploadInstructions.vue` | `dandi upload` → `dandi upload -i <instanceName>` |
| `web/src/views/DandisetLandingView/DownloadDialog.vue` (x3) | "DANDI CLI" UI text |

Backend — use `settings.DANDI_INSTANCE_NAME`:

| File | What to replace |
|------|-----------------|
| `dandiapi/api/mail.py` (x6) | "DANDI:" prefix in email subjects |
| `dandiapi/api/admin.py` | Admin site header/title ("DANDI Admin") |
| `dandiapi/urls.py` | OpenAPI schema title ("DANDI Archive") |
| `dandiapi/api/templates/api/mail/new_user_message.txt` | "signed up for DANDI" |
| `dandiapi/api/templates/api/mail/pending_users_message.txt` | "new DANDI users" |
| `dandiapi/api/templates/api/account/base.html` | `<title>DANDI Archive</title>` (name part only) |

### Group 2 — Requires new branding configuration

Frontend — custom images, colors, URLs:

| File | What needs config |
|------|-------------------|
| `web/src/components/AppBar/AppBar.vue` | Logo asset, alt text |
| `web/src/components/AppBar/AppBar.vue` | `import logo from '@/assets/logo.svg'` |
| `web/src/views/HomeView/HomeView.vue` | Logo asset import |
| `web/src/views/HomeView/HomeView.vue` | Archive heading (Group 1 name + Group 2 tagline) |
| `web/src/plugins/vuetify.ts` | Brand color palettes (light + dark themes) |
| `web/src/utils/constants.ts` | 7 hardcoded `dandiarchive.org` URLs (about, blog, docs, help, hub, sandbox) |
| `web/src/components/DandiFooter.vue` | Copyright line (Group 1 name + Group 2 start year, team name) |
| `web/src/components/DandiFooter.vue` | Code of Conduct GitHub URL |
| `web/src/components/DandiFooter.vue` | Funding section (BRAIN Initiative, NIMH, AWS, Netlify) |
| `web/src/components/DandiFooter.vue` | Support section (`help@dandiarchive.org`, helpdesk URL) |
| `web/src/components/DandiFooter.vue` | GitHub commit/repo URL |
| `web/src/components/UserStatusBanner.vue` | Banner texts (Group 1 name + Group 2 support email) |
| `web/src/views/DandisetLandingView/ShareDialog.vue` | Twitter/X handle |
| `web/src/views/DandisetLandingView/ExternalDandisetServicesDialog.vue` | `sandbox.dandiarchive.org` staging detection URL |
| `web/src/views/DandisetLandingView/ExternalDandisetServicesDialog.vue` | `medit.dandiarchive.org` AI editor URL |
| `web/src/views/DandisetLandingView/DandisetLandingView.vue` | `help@dandiarchive.org` support email |

Frontend assets (not annotatable with comments):

| File | What it is |
|------|-----------|
| `web/src/assets/logo.svg` | Main logo displayed in AppBar and HomeView splash |
| `web/public/favicon.ico` | Browser tab icon |

Backend — custom URLs, domain, content:

| File | What needs config |
|------|-------------------|
| `dandiapi/api/migrations/0001_default_site.py` | Site domain (`api.dandiarchive.org`) and name |
| `dandiapi/api/templates/api/account/base.html` | Logo URL from GitHub (Group 2 image) |
| `dandiapi/api/templates/api/root_content.html` | Group 1 name + Group 2 about URL, support email |
| `dandiapi/api/templates/api/account/questionnaire_form.html` | Group 1 name + Group 2 support email |
| `dandiapi/api/templates/api/mail/rejected_user_message.txt` | Group 1 name + Group 2 support email, docs URL, team name |
| `dandiapi/api/templates/api/mail/approved_user_message.txt` | Group 1 name + Group 2 docs URLs, YouTube URL, team name |
| `dandiapi/api/templates/api/mail/registered_message.txt` | Group 1 name + Group 2 hub URL, docs URLs, YouTube URL, team name |

## Target: EMBER Archive

The first (and motivating) consumer of branding abstraction is
**EMBER** (Ecosystem for Multi-modal Brain-behavior Experimentation and Research),
an archive instance run by JHU/APL for the NIH BBQS Program.

- Web: https://emberarchive.org
- API: https://api-dandi.emberarchive.org
- Fork: https://github.com/aplbrain/dandi-archive (branch `prod`)
- Support email: `help@emberarchive.org`
- RRID: `RRID:SCR_026700`
- DOI prefix: `10.82754`

### How EMBER currently brands (from `git diff origin/master...gh-aplbrain/prod`)

EMBER maintains a hard fork with ~370 lines of branding-only diff across 47
files. The changes fall into these categories:

**String replacements** (pure find-and-replace "DANDI" → "EMBER-DANDI"):
- Email subjects in `mail.py` (6 occurrences)
- All email templates (registered, approved, rejected, pending, new_user)
- Admin site header/title in `admin.py`
- OpenAPI schema title in `urls.py`
- Page titles in `index.html`, `base.html`
- User-facing text in `UserStatusBanner.vue`, `CookieBanner.vue`,
  `DandisetLandingView.vue`, `root_content.html`, `questionnaire_form.html`
- Support email `help@dandiarchive.org` → `help@emberarchive.org`

**Visual identity**:
- New logo `web/src/assets/ember-logo.png` (replaces `logo.svg`)
- New favicon `web/public/favicon.ico`
- Brand color palette in `vuetify.ts`: light-blue → red/orange/yellow
- AppBar layout: added "EMBER-DANDI" text label next to logo
- Accent colors tweaked in `UserMenu.vue`, `SingleStat.vue`

**Content customization**:
- HomeView heading: "The DANDI Archive" → "The EMBER-DANDI Archive"
- HomeView tagline: adjusted to mention BBQS Program
- Footer: added JHU/APL copyright, changed NIMH → BBQS Program link,
  added Sentry and DANDI to funding sources, added `class="text-primary"` on links
- `CreateDandisetView`: "Embargo this Dandiset" → "Mark Dandiset Private"
- Registered message template: removed Jupyterhub/Slack references,
  added EMBER-specific getting-started links

**URL changes**:
- Added EMBER-specific URLs in `constants.ts` (`emberAboutUrl`, `emberDocumentationUrl`, etc.)
- AppBar nav: replaced `dandiAboutUrl`/`dandiHelpUrl` with EMBER equivalents,
  commented out Support link
- GitHub repo URLs: `dandi/dandi-archive` → `aplbrain/dandi-archive`

**Deployment/CI config** (not branding per se, but coupled):
- `.env.production`: OAuth, API root, Sentry DSN all point to `emberarchive.org`
- `.env.docker-compose*`: instance name `DEV-EMBER-DANDI`, RRID, DOI prefix
- GitHub Actions workflows: adjusted for EMBER deployment targets
- `netlify.toml`: different redirect rules
- `web/.env.production`: different OAuth client ID

**Functional additions** (beyond branding):
- `FileUploadInstructions.vue`: added `-i <instance>` flag to `dandi upload`
  command (fetches instance name from API — already a proper fix)
- `views/auth.py`: includes questionnaire answers in admin notification email
- `scripts/embargo_dandiset_blobs.py`, `scripts/rewrite_manifest_files.py`,
  `scripts/ember_maintenance.html`: EMBER-specific operational scripts

### Assessment

The EMBER fork confirms that our `TODO: BRANDING` annotations capture the
correct set of touchpoints. Comparing the two inventories:

**Already annotated and matching EMBER's changes**: all email subjects,
email templates, constants.ts URLs, vuetify theme, AppBar logo, HomeView
heading/tagline, CookieBanner, UserStatusBanner, DandiFooter, questionnaire
form, admin.py, urls.py, base.html, root_content.html, migration site name.

**Gaps discovered from EMBER diff** (now annotated):
- `dandiapi/api/admin.py` — admin site header/title
- `dandiapi/urls.py` — OpenAPI schema title
- `dandiapi/api/templates/api/account/base.html` — title + logo URL
- `dandiapi/api/templates/api/root_content.html` — archive name, about URL, support email
- `web/src/views/DandisetLandingView/DandisetLandingView.vue` — support email
- `web/src/components/FileBrowser/FileUploadInstructions.vue` — `dandi upload` command

**EMBER changes that are deployment-specific** (not branding annotations):
- `.env.production`, `.env.docker-compose*` — these are instance env configs
- GitHub Actions workflows — deployment targets
- `netlify.toml` — hosting configuration
- `scripts/ember_*` — operational scripts

**EMBER changes that are feature additions** (should be upstreamed separately):
- `FileUploadInstructions.vue` `-i` flag — already properly uses instance API
- `views/auth.py` questionnaire in email — useful for all instances

## Future Implementation Notes

_To be designed in detail later._ High-level direction based on research
(Nautobot pattern, Django context processors, Vue runtime config):

- **Backend**: A `BRANDING` settings dict with env-var overridable keys for
  all display names, URLs, support contacts, social handles, etc.
  Extend `/api/info/` to serve branding config to the frontend.

- **Frontend**: A Pinia branding store loaded from `/api/info/` at startup.
  Components replace hardcoded strings with store references. CSS custom
  properties for brand colors. Dynamic logo/favicon from config URLs.

- **CI guard**: The existing `scripts/check-no-hardcoded-dandi.sh` (from PR
  #2765) catches regressions in `.vue`/`.ts` files. May be extended to cover
  Python files and templates.
