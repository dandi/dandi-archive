<template>
  <v-form
    style="width: 100%;"
    @submit="performSearch"
  >
    <v-text-field
      :model-value="$route.query.search"
      placeholder="Search Dandisets free form or with operators, e.g. try neuropixels species:mouse created_after:2024-01-01"
      variant="outlined"
      hide-details
      :density="dense ? 'compact' : undefined"
      bg-color="white"
      color="black"
      @update:model-value="updateSearch"
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
  </v-form>
</template>

<script setup lang="ts">
import { ref } from 'vue';
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
const currentSearch = ref(route.query.search || '');

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
  { example: 'standard:nwb', description: 'Has assets in a data standard' },
  { example: 'file_type:nwb', description: 'Has assets of a file type (nwb, image, text, video)' },
  { example: 'owner:jdoe', description: 'Owned by a user (username/email; or "owner:me")' },
];

function updateSearch(search: string) {
  currentSearch.value = search;
}

function performSearch(evt: Event) {
  evt.preventDefault(); // prevent form submission from refreshing page

  if (currentSearch.value === route.query.search) {
    // nothing has changed, do nothing
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
