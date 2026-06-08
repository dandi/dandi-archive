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

    <!-- Operator suggestions, GitHub-style. Teleported to the body so the
         toolbar's `overflow: hidden` doesn't clip it, and positioned manually
         beneath the input. Focus stays in the input (mousedown is prevented on
         the list) so the user can keep typing and use the keyboard to select. -->
    <Teleport to="body">
      <v-card
        v-if="showSuggestions"
        class="operator-suggestions py-1"
        :style="dropdownStyle"
        elevation="6"
        role="listbox"
      >
        <v-list
          density="compact"
          class="py-0"
        >
          <v-list-item
            v-for="(op, i) in suggestions"
            :key="op.key"
            :active="i === highlightedIndex"
            role="option"
            :aria-selected="i === highlightedIndex"
            @mousedown.prevent
            @mouseenter="highlightedIndex = i"
            @click="applyOperator(op)"
          >
            <template #title>
              <code class="operator-key">{{ op.key }}:</code><code
                v-if="op.example"
                class="operator-example"
              >{{ op.example }}</code>
            </template>
            <template #subtitle>
              {{ op.description }}
            </template>
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
  { example: 'technique:"patch clamp"', description: 'Has assets using a measurement technique' },
  { example: 'file_type:nwb', description: 'Has assets of a file type (nwb, image, text, video)' },
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

// --- Autocomplete state ---------------------------------------------------

const inputEl = ref<HTMLInputElement | null>(null);
const focused = ref(false);
// Set when the user presses Escape; cleared as soon as they type again.
const dismissed = ref(false);
const highlightedIndex = ref(-1);
// The whitespace-delimited token currently under the cursor.
const currentToken = ref('');

function getCurrentToken(text: string, cursor: number): { start: number; token: string } {
  const before = text.slice(0, cursor);
  const start = before.lastIndexOf(' ') + 1;
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

const suggestions = computed(() => {
  const token = currentToken.value;
  // Once the user has typed the colon, they're entering a value, not picking
  // an operator — stop suggesting.
  if (token.includes(':')) {
    return [];
  }
  const q = token.toLowerCase();
  if (!q) {
    return searchOperators;
  }
  return searchOperators.filter((op) => op.key.toLowerCase().includes(q));
});

// Auto-highlight the first match while the user is actively typing an operator
// prefix, but highlight nothing when simply browsing the full list (empty
// token) so that Enter submits the search instead of inserting an operator.
watch(suggestions, (list) => {
  highlightedIndex.value = currentToken.value && list.length ? 0 : -1;
});

const showSuggestions = computed(
  () => focused.value && !dismissed.value && suggestions.value.length > 0,
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
  return {
    position: 'fixed' as const,
    top: `${rect.value.bottom + 2}px`,
    left: `${rect.value.left}px`,
    width: `${rect.value.width}px`,
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

function applyOperator(op: { key: string }) {
  const el = inputEl.value;
  const cursor = el ? (el.selectionStart ?? searchText.value.length) : searchText.value.length;
  const { start } = getCurrentToken(searchText.value, cursor);
  const before = searchText.value.slice(0, start);
  const after = searchText.value.slice(cursor);
  const insert = `${op.key}:`;
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

function onKeydown(evt: KeyboardEvent) {
  if (evt.target instanceof HTMLInputElement) {
    inputEl.value = evt.target;
  }
  if (!showSuggestions.value) {
    return;
  }
  const count = suggestions.value.length;
  if (evt.key === 'ArrowDown') {
    evt.preventDefault();
    highlightedIndex.value = (Math.max(highlightedIndex.value, -1) + 1) % count;
  } else if (evt.key === 'ArrowUp') {
    evt.preventDefault();
    highlightedIndex.value = (highlightedIndex.value <= 0 ? count : highlightedIndex.value) - 1;
  } else if ((evt.key === 'Enter' || evt.key === 'Tab') && highlightedIndex.value >= 0) {
    // Select the highlighted operator. Preventing default stops the form from
    // submitting (Enter) or moving focus away (Tab) so typing can continue.
    evt.preventDefault();
    applyOperator(suggestions.value[highlightedIndex.value]);
  } else if (evt.key === 'Escape') {
    evt.preventDefault();
    dismissed.value = true;
  }
}

function performSearch(evt: Event) {
  evt.preventDefault(); // prevent form submission from refreshing page

  if (searchText.value === (route.query.search || '')) {
    // nothing has changed, do nothing
    return;
  }
  if (route.name !== 'searchDandisets') {
    router.push({
      name: 'searchDandisets',
      query: {
        search: searchText.value,
      },
    });
  } else {
    router.replace({
      ...route,
      query: {
        ...route.query,
        search: searchText.value,
      },
    } as RouteLocationRaw);
  }
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
  max-height: 320px;
  overflow-y: auto;
}
.operator-suggestions .operator-key {
  font-weight: 600;
  color: #4051b5;
}
.operator-suggestions .operator-example {
  color: rgba(0, 0, 0, 0.5);
}
</style>
