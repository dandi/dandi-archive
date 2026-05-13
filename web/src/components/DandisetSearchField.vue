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
    <!--
      Autocomplete dropdown. Anchored to the v-form (the wrapping container)
      so it spans the full width of the search field. We control visibility
      manually via `autocompleteOpen` and reposition the highlighted item via
      `selectedIndex` so arrow keys in the input drive selection.
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
        <v-list-item
          v-for="(op, i) in suggestions"
          :key="op.name"
          :active="i === selectedIndex"
          @mousedown.prevent="insertOperator(op)"
          @mouseenter="selectedIndex = i"
        >
          <v-list-item-title>
            <code>{{ op.name }}:</code>
            <span class="text-grey-darken-1 ml-2 text-caption">{{ op.valueExample }}</span>
          </v-list-item-title>
          <v-list-item-subtitle>{{ op.description }}</v-list-item-subtitle>
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
import {
  OPERATORS,
  suggestionsFor,
  tokenAtCursor,
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

// We anchor the dropdown to the <form> wrapping the field so its width
// matches the field. Capture the form element after mount.
function captureFormEl() {
  // The v-form root element is the actual DOM <form>; v-text-field exposes
  // its <input> via $el. We want the form for layout, the input for cursor.
  const inputComponent = searchInputRef.value;
  if (!inputComponent) return;
  const inputEl = (inputComponent.$el as HTMLElement | undefined)?.querySelector('input');
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

function inputElement(): HTMLInputElement | null {
  const inputComponent = searchInputRef.value;
  if (!inputComponent) return null;
  return (inputComponent.$el as HTMLElement | undefined)?.querySelector('input') ?? null;
}

const suggestions = computed(() => {
  const token = tokenAtCursor(currentSearch.value, cursor.value);
  return suggestionsFor(token.text);
});

// Keep selection in range when the suggestion list changes.
watch(suggestions, (next) => {
  if (selectedIndex.value >= next.length) {
    selectedIndex.value = 0;
  }
});

function syncCursorAndSuggest() {
  captureFormEl();
  const el = inputElement();
  if (!el) return;
  cursor.value = el.selectionStart ?? currentSearch.value.length;
  // Re-evaluate visibility based on whether there are matches at the new
  // cursor position. Always open while focused if there's at least one.
  autocompleteOpen.value = suggestions.value.length > 0;
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

function insertOperator(op: typeof OPERATORS[number]) {
  const text = currentSearch.value;
  const { start, end } = tokenAtCursor(text, cursor.value);
  const replacement = `${op.name}:`;
  currentSearch.value = text.slice(0, start) + replacement + text.slice(end);
  const newCursor = start + replacement.length;
  // Focus the input and move the cursor right after the inserted colon so
  // the user can immediately start typing the value.
  nextTick(() => {
    const el = inputElement();
    if (el) {
      el.focus();
      el.setSelectionRange(newCursor, newCursor);
    }
    cursor.value = newCursor;
    autocompleteOpen.value = false;
  });
}

function onEnter(evt: KeyboardEvent) {
  // If the autocomplete is open with a valid selection, take that — Enter
  // selects the highlighted operator instead of submitting the search.
  if (autocompleteOpen.value && suggestions.value.length > 0) {
    const op = suggestions.value[selectedIndex.value];
    if (op) {
      evt.preventDefault();
      insertOperator(op);
      return;
    }
  }
  performSearch(evt);
}

function onTabComplete(evt: KeyboardEvent) {
  // Tab also completes the highlighted suggestion (familiar from terminal /
  // editor autocomplete UIs); falls through to the browser default if the
  // dropdown isn't open.
  if (autocompleteOpen.value && suggestions.value.length > 0) {
    const op = suggestions.value[selectedIndex.value];
    if (op) {
      evt.preventDefault();
      insertOperator(op);
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
  /* Match the input's width and cap the height so a long list doesn't push
   * other content off-screen — internal scroll instead. */
  min-width: 100%;
  max-height: min(60vh, 480px);
  overflow-y: auto;
}
.advanced-search-autocomplete code {
  font-size: 0.9em;
}
</style>
