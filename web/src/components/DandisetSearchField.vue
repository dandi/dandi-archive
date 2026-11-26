<template>
  <v-form
    class="search-field-form"
    @submit="performSearch"
  >
    <v-text-field
      v-model="searchText"
      placeholder="Search Dandisets free form or with operators, e.g. try neuropixels species:mouse created_after:2024-01-01"
      variant="outlined"
      hide-details
      autocomplete="off"
      :density="dense ? 'compact' : undefined"
      bg-color="white"
      color="black"
      role="combobox"
      aria-autocomplete="list"
      :aria-expanded="showSuggestions"
      aria-controls="operator-suggestions"
      :aria-activedescendant="highlightedIndex >= 0 ? `operator-option-${highlightedIndex}` : undefined"
      @focus="onFocus"
      @blur="onBlur"
      @keydown="onKeydown"
      @keyup="updateToken"
      @click="updateToken"
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
          <v-card
            class="pa-3 advanced-search-help"
          >
            <div class="text-subtitle-2 mb-2">
              Advanced search operators
            </div>
            <div class="text-body-2 mb-2">
              Combine free text with <code>key:value</code> filters.
              Quote multi-word values: <code>technique:"spike sorting"</code>.
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

    <!-- Operator suggestions, styled after GitHub's search filter menu: a
         compact menu with a heading and one-line rows, so it reads as a set of
         options, not a history. Teleported to the body so the toolbar's
         `overflow: hidden` doesn't clip it, and positioned by hand beneath the
         input. Focus stays in the input (mousedown is prevented on the menu)
         so the user can keep typing; nothing is selected until they use the
         arrow keys or click, so Enter always searches for what was typed. -->
    <Teleport to="body">
      <v-card
        v-if="showSuggestions"
        class="operator-suggestions"
        :style="dropdownStyle"
        elevation="4"
        rounded="lg"
        border
        @mousedown.prevent
      >
        <div class="operator-suggestions-heading d-flex">
          {{ menu.heading }}
          <span
            v-if="menu.detailHeading"
            class="ml-auto"
          >{{ menu.detailHeading }}</span>
        </div>
        <div
          v-if="menu.loading"
          class="operator-suggestions-status"
        >
          Loading values…
        </div>
        <v-list
          id="operator-suggestions"
          density="compact"
          class="py-1"
          role="listbox"
        >
          <v-list-item
            v-for="(item, i) in menu.items"
            :id="`operator-option-${i}`"
            :key="item.id"
            :active="i === highlightedIndex"
            role="option"
            :aria-selected="i === highlightedIndex"
            min-height="32"
            class="operator-option"
            @click="item.apply()"
          >
            <!-- A plain title attribute: v-list-item's own `title` prop would render it as text. -->
            <div
              class="d-flex align-center ga-3"
              :title="item.tooltip"
            >
              <v-icon
                v-if="item.icon"
                size="small"
              >
                {{ item.icon }}
              </v-icon>
              <span class="operator-key">{{ item.label }}</span>
              <span class="operator-example ml-auto">{{ item.detail }}</span>
            </div>
          </v-list-item>
        </v-list>
      </v-card>
    </Teleport>
  </v-form>
</template>

<script setup lang="ts">
import {
  ref, computed, watch, nextTick, onMounted, onUnmounted,
} from 'vue';
import type { RouteLocationRaw } from 'vue-router';
import { useRoute } from 'vue-router';
import router from '@/router';
import { client } from '@/rest';

defineProps({
  dense: {
    type: Boolean,
    required: false,
    default: true,
  },
});

const route = useRoute();
const searchText = ref((route.query.search as string) || '');

// Keep the field in sync when the route's search param changes elsewhere
// (e.g. navigating to a different search, or clearing it).
watch(() => route.query.search, (val) => {
  searchText.value = (val as string) || '';
});

const operatorHelp = [
  { example: 'created_after:2024-01-01', description: 'Created on or after a date' },
  { example: 'created_before:2024-01-01', description: 'Created before a date' },
  { example: 'modified_after:2024-01-01', description: 'Last modified on or after a date' },
  { example: 'modified_before:2024-01-01', description: 'Last modified before a date' },
  { example: 'published_after:2024-01-01', description: 'Most recent publication on or after' },
  { example: 'published_before:2024-01-01', description: 'Most recent publication before' },
  { example: 'species:mouse', description: 'Has assets attributed to a species' },
  { example: 'approach:electrophysiology', description: 'Has assets using an approach' },
  { example: 'technique:"spike sorting"', description: 'Has assets using a measurement technique' },
  { example: 'standard:nwb', description: 'Has assets in a data standard (e.g. nwb, bids)' },
  { example: 'variable:LFP', description: 'Contains a measured variable / neurodata type' },
  { example: 'owner:"Jane Doe"', description: 'Owned by a user (name, GitHub username, or email)' },
];

// The set of operators we suggest, derived from the help table so the two
// stay in sync. The key is the part before the colon (e.g. `species`) and the
// example is the part after it (e.g. `2024-01-01`), shown as a format hint.
const searchOperators = operatorHelp.map((op) => {
  const colon = op.example.indexOf(':');
  return {
    key: op.example.slice(0, colon),
    example: op.example.slice(colon + 1),
    description: op.description,
  };
});

// An icon per operator in the suggestions menu. Operators without one get a
// generic filter icon.
const OPERATOR_ICONS: Record<string, string> = {
  created_after: 'mdi-calendar-start',
  created_before: 'mdi-calendar-end',
  modified_after: 'mdi-calendar-edit',
  modified_before: 'mdi-calendar-edit',
  published_after: 'mdi-calendar-check',
  published_before: 'mdi-calendar-check',
  species: 'mdi-paw',
  approach: 'mdi-flask-outline',
  technique: 'mdi-tools',
  standard: 'mdi-file-certificate-outline',
  variable: 'mdi-chart-line',
  owner: 'mdi-account-outline',
};

// --- Autocomplete state ---------------------------------------------------

const inputEl = ref<HTMLInputElement | null>(null);
const focused = ref(false);
// Set when the user presses Escape; cleared as soon as they type again.
const dismissed = ref(false);
const highlightedIndex = ref(-1);
// The whitespace-delimited token currently under the cursor.
const currentToken = ref('');

// The token under the cursor runs back to the last space that isn't inside
// double quotes, so `species:"house mo` is one token.
function getCurrentToken(text: string, cursor: number): { start: number; token: string } {
  const before = text.slice(0, cursor);
  let start = 0;
  let inQuotes = false;
  for (let i = 0; i < before.length; i += 1) {
    if (before[i] === '"') {
      inQuotes = !inQuotes;
    } else if (before[i] === ' ' && !inQuotes) {
      start = i + 1;
    }
  }
  return { start, token: before.slice(start) };
}

function updateToken() {
  const el = inputEl.value;
  const cursor = el ? (el.selectionStart ?? searchText.value.length) : searchText.value.length;
  currentToken.value = getCurrentToken(searchText.value, cursor).token;
}

// Typing clears an Escape dismissal and re-evaluates the token under the cursor.
watch(searchText, () => {
  dismissed.value = false;
  updateToken();
});

const operatorSuggestions = computed(() => {
  const token = currentToken.value;
  // Once the user has typed the colon, they're entering a value, not picking
  // an operator.
  if (token.includes(':')) {
    return [];
  }
  const q = token.toLowerCase();
  if (!q) {
    return searchOperators;
  }
  // Match the start of the operator or of one of its words ("pub" or "after"
  // for published_after), not any substring: "ate" shouldn't offer created_*.
  return searchOperators.filter((op) => op.key.toLowerCase().split('_').concat(op.key.toLowerCase())
    .some((word) => word.startsWith(q)));
});

// --- Value suggestions for categorical operators ---------------------------

// Operators whose values come from the dandisets' assets summaries. After
// `species:` and the like, the menu lists the values found on DANDI, most
// common first. Headings name what the counts on the right are.
const VALUE_OPERATOR_HEADINGS: Record<string, string> = {
  species: 'Species',
  approach: 'Approaches',
  technique: 'Measurement techniques',
  standard: 'Data standards',
  variable: 'Variables measured',
};
// Long lists (e.g. variables) are cut to this many matches; typing narrows them.
const MAX_VALUE_SUGGESTIONS = 50;

interface OperatorValue {
  value: string;
  dandisets: number;
}

// Each operator's values, fetched once per page when first needed.
const operatorValues = ref<Record<string, OperatorValue[]>>({});
const loadingValuesFor = ref<string | null>(null);

// `species:"house mo` -> { key: 'species', partial: 'house mo' }; null when
// the token isn't a categorical operator followed by its colon.
const valueToken = computed(() => {
  const match = /^([a-z_]+):(.*)$/.exec(currentToken.value);
  if (!match || !(match[1] in VALUE_OPERATOR_HEADINGS)) {
    return null;
  }
  return { key: match[1], partial: match[2].replace(/^"/, '').replace(/"$/, '') };
});

async function loadOperatorValues(key: string) {
  if (operatorValues.value[key] || loadingValuesFor.value === key) {
    return;
  }
  loadingValuesFor.value = key;
  try {
    const { data } = await client.get<OperatorValue[]>('search/operator-values/', { params: { operator: key } });
    operatorValues.value = { ...operatorValues.value, [key]: data };
  } catch {
    // Without a list the field still works: the user types the value.
    operatorValues.value = { ...operatorValues.value, [key]: [] };
  } finally {
    if (loadingValuesFor.value === key) {
      loadingValuesFor.value = null;
    }
  }
}

watch(() => valueToken.value?.key, (key) => {
  if (key) {
    loadOperatorValues(key);
  }
});

// Values with spaces (most of them) are quoted so the parser keeps them whole.
function formatValue(value: string): string {
  const plain = value.replaceAll('"', '');
  return /\s/.test(plain) ? `"${plain}"` : plain;
}

// --- The menu: operators, or one operator's values -------------------------

interface MenuItem {
  id: string;
  label: string;
  detail: string;
  tooltip?: string;
  icon?: string;
  apply: () => void;
}

const menu = computed<{ heading: string; detailHeading?: string; items: MenuItem[]; loading: boolean }>(() => {
  const vt = valueToken.value;
  if (vt) {
    const all = operatorValues.value[vt.key];
    const partial = vt.partial.toLowerCase();
    const matches = (all ?? [])
      .filter((v) => v.value.toLowerCase().includes(partial))
      .slice(0, MAX_VALUE_SUGGESTIONS);
    return {
      heading: VALUE_OPERATOR_HEADINGS[vt.key],
      detailHeading: matches.length ? 'Dandisets' : undefined,
      loading: !all,
      items: matches.map((v) => ({
        id: `${vt.key}:${v.value}`,
        label: v.value,
        detail: String(v.dandisets),
        tooltip: `${v.value} (${v.dandisets} dandiset${v.dandisets === 1 ? '' : 's'})`,
        apply: () => applyValue(vt.key, v.value),
      })),
    };
  }
  return {
    heading: 'Narrow your search',
    loading: false,
    items: operatorSuggestions.value.map((op) => ({
      id: op.key,
      label: `${op.key}:`,
      detail: op.example,
      tooltip: op.description,
      icon: OPERATOR_ICONS[op.key] || 'mdi-filter-variant',
      apply: () => applyOperator(op),
    })),
  };
});

// Nothing is highlighted until the user moves into the list with the arrow
// keys, so Enter searches for what was typed (e.g. a free-text "species")
// instead of turning it into an operator or value.
watch(() => menu.value.items.map((item) => item.id).join('\n'), () => {
  highlightedIndex.value = -1;
});

const showSuggestions = computed(
  () => focused.value && !dismissed.value && (menu.value.items.length > 0 || menu.value.loading),
);

// --- Dropdown positioning (teleported, so we place it by hand) -------------

const rect = ref<DOMRect | null>(null);
function updateRect() {
  rect.value = inputEl.value?.getBoundingClientRect() ?? null;
}

const dropdownStyle = computed(() => {
  if (!rect.value) {
    return {};
  }
  // A compact menu like GitHub's: up to 360px wide whatever the input's width
  // (the input is narrow on phones), kept inside the window.
  const width = Math.min(360, window.innerWidth - 16);
  const left = Math.max(8, Math.min(rect.value.left, window.innerWidth - width - 8));
  return {
    position: 'fixed' as const,
    top: `${rect.value.bottom + 2}px`,
    left: `${left}px`,
    width: `${width}px`,
    zIndex: 2400,
  };
});

onMounted(() => {
  window.addEventListener('scroll', updateRect, true);
  window.addEventListener('resize', updateRect);
});
onUnmounted(() => {
  window.removeEventListener('scroll', updateRect, true);
  window.removeEventListener('resize', updateRect);
});

// --- Event handlers --------------------------------------------------------

function onFocus(evt: FocusEvent) {
  focused.value = true;
  dismissed.value = false;
  if (evt.target instanceof HTMLInputElement) {
    inputEl.value = evt.target;
  }
  updateToken();
  updateRect();
}

function onBlur() {
  focused.value = false;
}

// Replace the token under the cursor with `insert`, leaving the cursor after it.
function replaceToken(insert: string) {
  const el = inputEl.value;
  const cursor = el ? (el.selectionStart ?? searchText.value.length) : searchText.value.length;
  const { start } = getCurrentToken(searchText.value, cursor);
  const before = searchText.value.slice(0, start);
  const after = searchText.value.slice(cursor);
  searchText.value = `${before}${insert}${after}`;
  const newCursor = before.length + insert.length;
  nextTick(() => {
    if (el) {
      el.focus();
      el.setSelectionRange(newCursor, newCursor);
      currentToken.value = getCurrentToken(searchText.value, newCursor).token;
    }
  });
}

function applyOperator(op: { key: string }) {
  replaceToken(`${op.key}:`);
}

// A chosen value ends the term, so a space follows it, ready for the next one.
function applyValue(key: string, value: string) {
  replaceToken(`${key}:${formatValue(value)} `);
}

function onKeydown(evt: KeyboardEvent) {
  if (evt.target instanceof HTMLInputElement) {
    inputEl.value = evt.target;
  }
  if (!showSuggestions.value) {
    return;
  }
  const { items } = menu.value;
  const count = items.length;
  // While values are loading the menu has no rows to move through.
  if ((evt.key === 'ArrowDown' || evt.key === 'ArrowUp') && !count) {
    return;
  }
  if (evt.key === 'ArrowDown') {
    evt.preventDefault();
    highlightedIndex.value = (Math.max(highlightedIndex.value, -1) + 1) % count;
  } else if (evt.key === 'ArrowUp') {
    evt.preventDefault();
    highlightedIndex.value = (highlightedIndex.value <= 0 ? count : highlightedIndex.value) - 1;
  } else if (evt.key === 'Enter' && highlightedIndex.value >= 0) {
    // Insert the operator the user arrowed to. Preventing default stops the
    // form from submitting so typing can continue.
    evt.preventDefault();
    items[highlightedIndex.value].apply();
  } else if (evt.key === 'Tab' && count && (highlightedIndex.value >= 0 || currentToken.value)) {
    // Tab completes the highlighted operator, or the top match while typing
    // one. It never submits, so it can't get in the way of a search.
    evt.preventDefault();
    items[Math.max(highlightedIndex.value, 0)].apply();
  } else if (evt.key === 'Escape') {
    evt.preventDefault();
    dismissed.value = true;
  }
}

function performSearch(evt: Event) {
  evt.preventDefault(); // prevent form submission from refreshing page
  // A chosen value leaves a trailing space for the next term; don't search on it.
  const query = searchText.value.trim();

  if (route.name === 'searchDandisets' || route.name === 'myDandisets') {
    // Already on a search page: only re-run the search if the query actually
    // changed, so pressing Enter on an unchanged field is a no-op. Staying on
    // the current page keeps its context — on "My Dandisets" this scopes the
    // search to the user's own dandisets (including embargoed).
    if (query === (route.query.search || '')) {
      return;
    }
    router.replace({
      ...route,
      query: {
        ...route.query,
        search: query,
      },
    } as RouteLocationRaw);
    return;
  }

  // Searching from anywhere else (the home page, a dandiset landing page)
  // takes the user to the search results page. An empty query is allowed —
  // it lists all dandisets.
  router.push({
    name: 'searchDandisets',
    query: {
      search: query,
    },
  });
}
</script>

<style scoped>
.search-field-form {
  width: 100%;
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
</style>

<style>
/* Unscoped: the suggestions card is teleported to <body>, outside this
 * component's scoped-style boundary. */
.operator-suggestions {
  max-height: 360px;
  overflow-y: auto;
}
.operator-suggestions .operator-suggestions-heading {
  padding: 8px 16px 4px;
  font-size: 0.75rem;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.6);
}
.operator-suggestions .operator-option .v-icon {
  opacity: 0.7;
}
.operator-suggestions .operator-suggestions-status {
  padding: 4px 16px 8px;
  font-size: 0.875rem;
  color: rgba(0, 0, 0, 0.6);
}
/* Long values (e.g. measurement techniques) end in an ellipsis; the full
 * value is in the row's tooltip. */
.operator-suggestions .operator-key {
  font-size: 0.875rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}
.operator-suggestions .operator-example {
  font-size: 0.75rem;
  color: rgba(0, 0, 0, 0.5);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
  flex-shrink: 0;
}
</style>
