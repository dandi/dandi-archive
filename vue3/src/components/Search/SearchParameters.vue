<script setup lang="ts">
import GenotypeSearch from './forms/GenotypeForm.vue';
import SpeciesSearch from './forms/SpeciesForm.vue';
import FileType from './forms/FileTypeForm.vue';
import FileSize from './forms/FileSizeForm.vue';

const SEARCH_PARAMS = [
  { name: 'File Size (bytes)', component: FileSize },
  { name: 'File Type', component: FileType },
  { name: 'Genotype', component: GenotypeSearch },
  { name: 'Species', component: SpeciesSearch },
];
</script>

<template>
  <v-container class="pa-3">
    <span class="text-h4">Search Assets</span>
    <v-sheet class="ma-2">
      <v-card
        v-for="(param, i) in SEARCH_PARAMS"
        :key="i"
        outlined
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
