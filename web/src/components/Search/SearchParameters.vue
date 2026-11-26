<script setup lang="ts">
import { computed } from 'vue';
import { useDisplay } from 'vuetify';
import GenotypeSearch from './forms/GenotypeForm.vue';
import SpeciesSearch from './forms/SpeciesForm.vue';
import FileType from './forms/FileTypeForm.vue';
import FileSize from './forms/FileSizeForm.vue';
import { searchParameters } from './store';

const SEARCH_PARAMS = [
  { name: 'File Size (bytes)', component: FileSize },
  { name: 'File Type', component: FileType },
  { name: 'Genotype', component: GenotypeSearch },
  { name: 'Species', component: SpeciesSearch },
];

// Below md the filters sit above the results, so they start collapsed to keep the results in view.
const display = useDisplay();
const collapseFilters = computed(() => display.smAndDown.value);

const activeFilterCount = computed(() => Object.values(searchParameters).filter(
  // An emptied number field holds '' at runtime, so compare as a string.
  (value) => (Array.isArray(value) ? value.length > 0 : String(value ?? '') !== ''),
).length);
</script>

<template>
  <v-container class="pa-3">
    <span class="text-h4">Search Assets</span>
    <v-expansion-panels
      v-if="collapseFilters"
      class="mt-4 px-2"
    >
      <v-expansion-panel>
        <v-expansion-panel-title>
          Filters
          <span
            v-if="activeFilterCount"
            class="ml-1"
          >({{ activeFilterCount }} active)</span>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-card
            v-for="(param, i) in SEARCH_PARAMS"
            :key="i"
            variant="outlined"
            class="my-4"
          >
            <v-card-title>
              {{ param.name }}
            </v-card-title>
            <v-card-text>
              <component :is="param.component" />
            </v-card-text>
          </v-card>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
    <v-sheet
      v-else
      class="ma-2"
    >
      <v-card
        v-for="(param, i) in SEARCH_PARAMS"
        :key="i"
        variant="outlined"
        class="ma-4"
      >
        <v-card-title>
          {{ param.name }}
        </v-card-title>
        <v-card-text>
          <component :is="param.component" />
        </v-card-text>
      </v-card>
    </v-sheet>
  </v-container>
</template>
