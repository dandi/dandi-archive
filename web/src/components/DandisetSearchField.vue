<template>
  <v-form
    style="width: 100%;"
    class="advanced-search-field"
    @submit="performSearch"
  >
    <v-text-field
      ref="searchInputRef"
      :model-value="currentSearch"
      placeholder="Search Dandisets free form or with operators, e.g. try neuropixels species:mouse created_after:2024-01-01"
      variant="outlined"
      hide-details
      :density="dense ? 'compact' : undefined"
      bg-color="white"
      color="black"
      autocomplete="off"
      @update:model-value="onInput"
      @focus="onFocus"
      @click="syncCursorAndSuggest"
      @keyup="syncCursorAndSuggest"
      @keydown.down.prevent="moveSelection(1)"
      @keydown.up.prevent="moveSelection(-1)"
      @keydown.enter="onEnter"
      @keydown.tab="onTabComplete"
      @keydown.esc="autocompleteOpen = false"
      @blur="onBlur"
    >
      <template #prepend-inner>
        <v-icon @click="performSearch">
          mdi-magnify
        </v-icon>
      </template>
      <template #append-inner>
        <v-menu
          :close-on-content-click="false"
          location="bottom end"
          offset="8"
        >
          <template #activator="{ props: activatorProps }">
            <v-icon
              v-bind="activatorProps"
              size="small"
              color="grey-darken-1"
              aria-label="Show advanced search syntax help"
            >
              mdi-help-circle-outline
            </v-icon>
          </template>
          <v-card class="pa-3 advanced-search-help">
            <div class="text-subtitle-2 mb-2">
              Advanced search operators
            </div>
            <div class="text-body-2 mb-2">
              Combine free text with <code>key:value</code> filters.
              Quote multi-word values: <code>technique:"patch clamp"</code>.
            </div>
            <v-table density="compact">
              <tbody>
                <tr
                  v-for="op in operatorHelp"
                  :key="op.example"
                >
                  <td class="example-cell">
                    <code>{{ op.example }}</code>
                  </td>
                  <td class="text-caption">
                    {{ op.description }}
                  </td>
                </tr>
              </tbody>
            </v-table>
          </v-card>
        </v-menu>
      </template>
    </v-text-field>
    <!--
      Autocomplete dropdown. Anchored to the v-form (the wrapping container)
      so it spans the full width of the search field; teleported (default
      v-menu behavior, no `attach`) so it escapes any sibling stacking
      context like the result-count panel below.
    -->
    <v-menu
      v-model="autocompleteOpen"
      :activator="formEl ?? undefined"
      :close-on-content-click="false"
      :open-on-click="false"
      :open-on-focus="false"
      location="bottom start"
      transition="false"
      :min-width="dropdownWidth"
      :max-width="dropdownWidth"
    >
      <v-list
        v-if="suggestions.length"
        density="compact"
        class="advanced-search-autocomplete"
      >
        <!-- Header line indicating which mode the dropdown is in. -->
        <v-list-subheader v-if="mode.kind === 'value'">
          values for <code>{{ mode.operator.name }}:</code>
          <span
            v-if="speciesLoading"
            class="text-caption text-grey-darken-1 ml-2"
          >loading…</span>
        </v-list-subheader>
        <v-list-item
          v-for="(s, i) in suggestions"
          :key="suggestionKey(s)"
          :active="i === selectedIndex"
          @mousedown.prevent="insertSuggestion(s)"
          @mouseenter="selectedIndex = i"
        >
          <template v-if="s.kind === 'key'">
            <v-list-item-title>
              <code>{{ s.op.name }}:</code>
              <span class="text-grey-darken-1 ml-2 text-caption">{{ s.op.valueExample }}</span>
            </v-list-item-title>
            <v-list-item-subtitle>{{ s.op.description }}</v-list-item-subtitle>
          </template>
          <template v-else>
            <v-list-item-title>
              <code>{{ s.value }}</code>
            </v-list-item-title>
          </template>
        </v-list-item>
      </v-list>
    </v-menu>
  </v-form>
</template>

<script setup lang="ts">
import {
  computed, nextTick, onBeforeUnmount, onMounted, ref, watch,
} from 'vue';
import type { ComponentPublicInstance } from 'vue';
import type { RouteLocationRaw } from 'vue-router';
import { useRoute } from 'vue-router';
import router from '@/router';
import { client } from '@/rest';
import {
  type SearchOperator,
  keySuggestions,
  suggestModeAt,
  valueSuggestions,
} from '@/components/advancedSearchOperators';

defineProps({
  dense: {
    type: Boolean,
    required: false,
    default: true,
  },
});

const route = useRoute();
const currentSearch = ref<string>(String(route.query.search ?? ''));

// --- Help popover (existing) ---------------------------------------------------------
// Kept hand-curated so the popover stays a focused cheat-sheet rather than
// duplicating the autocomplete's full operator list. The autocomplete uses
// the canonical OPERATORS catalog from advancedSearchOperators.ts.
const operatorHelp = [
  { example: 'created_after:2024-01-01', description: 'Created on or after a date' },
  { example: 'modified_after:2024-01-01', description: 'Last modified on or after a date' },
  { example: 'published_after:2024-01-01', description: 'Most recent publication on or after' },
  { example: 'species:mouse', description: 'Has assets attributed to a species' },
  { example: 'approach:electrophysiology', description: 'Has assets using an approach' },
  { example: 'technique:"patch clamp"', description: 'Has assets using a measurement technique' },
  { example: 'standard:nwb', description: 'Has assets in a data standard' },
  { example: 'file_type:nwb', description: 'Has assets of a file type (nwb, image, text, video)' },
  { example: 'owner:"Jane Doe"', description: 'Owned by a user (name, username, or email)' },
  { example: 'contributor:"Doe, Jane"', description: 'Listed as a contributor (any role)' },
  { example: 'author:Doe', description: 'Listed as an Author' },
  { example: 'funder:NIH', description: 'Listed as a Funder' },
  { example: 'affiliation:Stanford', description: 'Affiliated with an organization' },
];

// --- Autocomplete state -------------------------------------------------------------

type Suggestion =
  | { kind: 'key'; op: SearchOperator }
  | { kind: 'value'; value: string };

const searchInputRef = ref<ComponentPublicInstance | null>(null);
const formEl = ref<HTMLElement | null>(null);
const autocompleteOpen = ref(false);
const selectedIndex = ref(0);
// Cursor position inside the underlying <input>; updated on every keyup/click.
const cursor = ref(0);
// Width of the form, used to size the autocomplete menu so it visually
// matches the search field. The menu itself teleports to the document body
// (default v-menu behavior, no `attach`) so it escapes any local stacking
// context — that's how it stays on top of sibling result panels below.
const dropdownWidth = ref(0);
// Live species values, fetched from `/search/species` when the cursor is in
// a `species:` value. Other value-suggesting operators use static lists
// from the operator catalog.
const speciesValues = ref<string[]>([]);
const speciesLoading = ref(false);
let speciesDebounce: number | null = null;
let speciesFetchSeq = 0;

// Mode is recomputed automatically from the current text + cursor position.
const mode = computed(() => suggestModeAt(currentSearch.value, cursor.value));

const suggestions = computed<Suggestion[]>(() => {
  const m = mode.value;
  if (m.kind === 'key') {
    return keySuggestions(m.prefix).map((op) => ({ kind: 'key', op }));
  }
  if (m.kind === 'value') {
    if (m.operator.name === 'species') {
      return speciesValues.value.map((value) => ({ kind: 'value', value }));
    }
    return valueSuggestions(m.operator, m.prefix)
      .map((value) => ({ kind: 'value', value }));
  }
  return [];
});

// Keep selection in range when the suggestion list changes.
watch(suggestions, (next) => {
  if (selectedIndex.value >= next.length) {
    selectedIndex.value = 0;
  }
});

// When the user is typing a species value, fetch live matches from the
// existing /search/species endpoint. Debounced + sequence-checked so a
// slow earlier response can't overwrite a faster later one.
watch(mode, (m) => {
  if (m.kind === 'value' && m.operator.name === 'species') {
    if (speciesDebounce) {
      clearTimeout(speciesDebounce);
    }
    speciesLoading.value = true;
    const seq = ++speciesFetchSeq;
    const prefix = m.prefix;
    speciesDebounce = window.setTimeout(async () => {
      try {
        const r = await client.get('/search/species', { params: { species: prefix } });
        if (seq === speciesFetchSeq) {
          // r.data follows DandiPagination — `results` is the value list.
          speciesValues.value = (r.data?.results ?? []) as string[];
        }
      } catch {
        if (seq === speciesFetchSeq) {
          speciesValues.value = [];
        }
      } finally {
        if (seq === speciesFetchSeq) {
          speciesLoading.value = false;
        }
      }
    }, 200);
  }
});

function inputElement(): HTMLInputElement | null {
  const inputComponent = searchInputRef.value;
  if (!inputComponent) return null;
  return (inputComponent.$el as HTMLElement | undefined)?.querySelector('input') ?? null;
}

function captureFormEl() {
  // The v-form root element is the actual DOM <form>; v-text-field exposes
  // its <input> via $el. We want the form for layout, the input for cursor.
  const inputEl = inputElement();
  if (inputEl?.form) {
    formEl.value = inputEl.form;
    dropdownWidth.value = inputEl.form.clientWidth;
  }
}

function updateDropdownWidth() {
  if (formEl.value) {
    dropdownWidth.value = formEl.value.clientWidth;
  }
}

onMounted(() => {
  // Capture the form element after the v-text-field's DOM is rendered, then
  // keep `dropdownWidth` in sync with the form on window resize so a wider
  // viewport → wider dropdown.
  nextTick(captureFormEl);
  window.addEventListener('resize', updateDropdownWidth);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', updateDropdownWidth);
});

function syncCursorAndSuggest() {
  captureFormEl();
  const el = inputElement();
  if (!el) return;
  cursor.value = el.selectionStart ?? currentSearch.value.length;
  // For value mode we always open the dropdown so the user sees the loading
  // header even if no values have come back yet; for key/none modes only
  // open when there are actual matches.
  autocompleteOpen.value = suggestions.value.length > 0 || mode.value.kind === 'value';
}

function onInput(value: string) {
  currentSearch.value = value;
  selectedIndex.value = 0;
  // The cursor moves before our @keyup fires, so query the input directly on
  // the next tick once Vue has flushed the model update.
  nextTick(syncCursorAndSuggest);
}

function onFocus() {
  syncCursorAndSuggest();
}

function onBlur() {
  // Defer so a click on a menu item registers before the menu closes.
  // (mousedown.prevent on the items also keeps focus, but this is belt + suspenders.)
  setTimeout(() => {
    autocompleteOpen.value = false;
  }, 150);
}

function moveSelection(delta: number) {
  if (!autocompleteOpen.value || suggestions.value.length === 0) return;
  const n = suggestions.value.length;
  selectedIndex.value = (selectedIndex.value + delta + n) % n;
}

function suggestionKey(s: Suggestion): string {
  return s.kind === 'key' ? `key:${s.op.name}` : `value:${s.value}`;
}

function spliceAndMoveCursor(start: number, end: number, replacement: string) {
  const text = currentSearch.value;
  currentSearch.value = text.slice(0, start) + replacement + text.slice(end);
  const newCursor = start + replacement.length;
  nextTick(() => {
    const el = inputElement();
    if (el) {
      el.focus();
      el.setSelectionRange(newCursor, newCursor);
    }
    cursor.value = newCursor;
    selectedIndex.value = 0;
  });
}

function insertSuggestion(s: Suggestion) {
  const m = mode.value;
  if (s.kind === 'key' && m.kind === 'key') {
    // Insert `name:` at the key position. Cursor lands right after the colon
    // — if the operator has value suggestions, the dropdown will switch to
    // value mode on the next sync (the user sees value options immediately).
    spliceAndMoveCursor(m.replaceStart, m.replaceEnd, `${s.op.name}:`);
  } else if (s.kind === 'value' && m.kind === 'value') {
    // Insert the chosen value, preserving the user's `key:` prefix. Quote
    // multi-word values so the parser sees them as a single token.
    const value = /\s/.test(s.value) ? `"${s.value}"` : s.value;
    spliceAndMoveCursor(m.replaceStart, m.replaceEnd, value);
    // After picking a value, the user is done with this operator — close
    // the dropdown so a stray Tab doesn't re-complete.
    nextTick(() => {
      autocompleteOpen.value = false;
    });
  }
}

function onEnter(evt: KeyboardEvent) {
  // Enter always submits the search — even when the dropdown is open. Users
  // need to be able to search for free-text terms (e.g. `publ`) that happen
  // to be a prefix of an operator name; auto-completing on Enter would make
  // those queries unreachable. Use Tab or click to complete instead.
  performSearch(evt);
}

function onTabComplete(evt: KeyboardEvent) {
  // Tab completes the highlighted suggestion (familiar from terminal /
  // editor autocomplete UIs); falls through to the browser default if the
  // dropdown isn't open or has no matches.
  if (autocompleteOpen.value && suggestions.value.length > 0) {
    const s = suggestions.value[selectedIndex.value];
    if (s) {
      evt.preventDefault();
      insertSuggestion(s);
    }
  }
}

function performSearch(evt: Event) {
  evt.preventDefault(); // prevent form submission from refreshing page
  autocompleteOpen.value = false;

  if (currentSearch.value === route.query.search) {
    return;
  }
  if (route.name !== 'searchDandisets') {
    router.push({
      name: 'searchDandisets',
      query: {
        search: currentSearch.value,
      },
    });
  } else {
    router.replace({
      ...route,
      query: {
        ...route.query,
        search: currentSearch.value,
      },
    } as RouteLocationRaw);
  }
}
</script>

<style scoped>
.advanced-search-field {
  position: relative;
}

.advanced-search-help {
  /* Sized responsively: wide enough for the longest example without wrapping,
   * but capped so it doesn't fill very wide monitors. */
  min-width: 420px;
  max-width: min(80vw, 720px);
}
.advanced-search-help .example-cell {
  /* Keep operator examples on a single line so they read like code. */
  white-space: nowrap;
}

.advanced-search-autocomplete {
  /* Cap the dropdown's height so a long list doesn't push other content
   * off-screen — internal scroll instead. Width is set via the v-menu's
   * min/max-width binding, so the list itself doesn't need a width. */
  max-height: min(60vh, 480px);
  overflow-y: auto;
}
.advanced-search-autocomplete code {
  font-size: 0.9em;
}
</style>
