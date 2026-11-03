---
name: vuetify-component-api
description: Use when writing or changing Vue components under web/src — especially when adding navigation, click handling, or layout/spacing to a Vuetify component, or when about to add a <style scoped> block, a wrapper <a>/<router-link>, or a JS click handler that navigates. Prefer Vuetify's own props and utility classes over custom CSS and imperative handlers.
---

# Prefer Vuetify's component API over custom CSS and handlers

The web frontend (`web/`) uses Vue 3 + Vuetify 3 + vue-router. Vuetify components
already cover most of what a feature needs: navigation, active state, spacing,
colors, elevation, alignment. Reach for the component's own props and Vuetify's
utility classes first. Custom `<style scoped>` blocks, wrapper elements, and
hand-written click handlers are a last resort — they duplicate framework
behavior, drift from the theme, and break when Vuetify's internal DOM changes.

Only 12 of the ~100 `.vue` files in `web/src` have a `<style>` block at all.
Adding one is a signal to stop and look for the prop first.

## Rules

1. **Navigation goes through `:to` / `:href`, not a click handler.**
   Most Vuetify components (`v-list-item`, `v-btn`, `v-card`, `v-chip`, `v-tab`,
   `v-breadcrumbs-item`, ...) accept `to` (router link) and `href` (plain link).
   Setting one turns the whole component into a real anchor, so right-click
   "Open link in new tab", middle-click, and ctrl/cmd-click all work for free.
   Never emulate this with `window.open(url, "_self")`, `location.value = ...`,
   or a `@click` that calls `router.push` — those produce a div the browser
   cannot treat as a link.

   Reserve `router.push` for navigation that is *not* a user clicking a thing:
   redirecting after a form submit, reacting to a search, syncing query params.

2. **Don't nest an `<a>` or `<router-link>` inside a component that can be one.**
   Wrapping the label in a link only makes the label clickable, which then
   tempts a stretched `::after` overlay plus `z-index` juggling to cover the
   rest of the row. Put the link on the component itself instead.

3. **Interactive children inside a linkified component need `@click.stop.prevent`.**
   `.stop` alone stops the handler chain but the anchor's default navigation
   still fires. Buttons, menu activators, and checkboxes inside a `:to`/`:href`
   row all need both modifiers — including activators bound via `v-bind` from a
   `v-menu`/`v-tooltip` slot, which need a bare `@click.stop.prevent`.

4. **Use `:active="false"` when a link shouldn't carry selected styling.**
   Vuetify derives `active` from route matching once `to` is set. Suppress it
   with the prop rather than overriding the resulting classes in CSS.

5. **Spacing, color, and alignment come from utility classes.**
   `ma-*`/`pa-*`, `text-*`, `bg-*`, `d-flex`, `align-*`, `justify-*`, `text-truncate`.
   Write CSS only for something Vuetify genuinely has no answer for, and say in a
   comment what that something is.

## Worked example

From [PR #2926](https://github.com/dandi/dandi-archive/pull/2926), review commit
[`31e3723`](https://github.com/dandi/dandi-archive/commit/31e3723d1ea0fde967fe5d1503b7e86295c9ccaf)
(`web/src/views/FileBrowserView/FileBrowser.vue`). The goal — make file-browser
rows behave like real links — was first implemented with a nested link plus a
stretched overlay, then rewritten to use `v-list-item`'s own props. Net: 12
lines added, 70 removed.

Before — nested link, overlay CSS, imperative handler:

```vue
<v-list-item class="item-row" @click="openItem(item)">
  <v-list-item-title>
    <a v-if="item.asset" class="item-link" :href="inlineURI(item.asset.asset_id)" @click.stop>
      {{ item.name }}
    </a>
    <router-link v-else class="item-link" :to="locationRoute(item.path)" @click.stop>
      {{ item.name }}
    </router-link>
  </v-list-item-title>
  <template #append>
    <v-btn icon variant="text" @click.stop="setItemToDelete(item)">...</v-btn>
  </template>
</v-list-item>
```

```ts
function openItem(item: AssetPath) {
  const { asset, path } = item;
  if (asset) {
    window.open(inlineURI(asset.asset_id), "_self");
  } else {
    location.value = path;
  }
}
```

```css
.item-row { position: relative; }
.item-link { color: inherit; text-decoration: none; }
.item-link:hover { text-decoration: underline; }
.item-link::after { content: ''; position: absolute; inset: 0; z-index: 1; }
.item-row :deep(.v-list-item__append) { position: relative; z-index: 2; }
```

After — the props do all of it; the handler, the wrapper links, and the entire
`<style scoped>` block are gone:

```vue
<!--
  Render each row as a real link so that
  the browser treats it as one: right click offers "Open link in new tab", and
  ctrl/cmd/middle click work as they do anywhere else. Buttons in the append
  slot stop the click and prevent its default so the row link isn't followed.
-->
<v-list-item
  color="primary"
  :href="item.asset ? inlineURI(item.asset.asset_id) : undefined"
  :to="item.asset ? undefined : locationRoute(item.path)"
  :active="false"
>
  <v-list-item-title :title="item.name">
    {{ item.name }}
  </v-list-item-title>
  <template #append>
    <v-btn icon variant="text" @click.stop.prevent="setItemToDelete(item)">...</v-btn>
    <v-btn v-bind="openWithProps" @click.stop.prevent>Open With</v-btn>
  </template>
</v-list-item>
```

Note `:href` and `:to` are mutually exclusive per row — pass `undefined` for the
one that doesn't apply rather than branching the whole element with `v-if`.

## Before you commit

- Any new `<style scoped>` rule: name the Vuetify prop or utility class you
  checked first, and why it didn't fit. `:deep()` into a Vuetify internal class
  (`.v-list-item__append`, ...) is a strong sign the prop was missed.
- Any new `@click` that navigates: replace it with `:to` or `:href`.
- Any new `position: absolute` / `z-index` used to enlarge a click target:
  the target component probably takes `to`/`href` itself.
- Linkified a component? Verify right-click, middle-click, and ctrl/cmd-click
  in the deploy preview, and that every button inside it still works and does
  *not* navigate.
