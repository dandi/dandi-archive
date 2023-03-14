<script setup lang="ts">
import GenotypeSearch from './forms/Genotype.vue';
import SpeciesSearch from './forms/Species.vue';
import FileType from './forms/FileType.vue';
import MeasurementTechniqueSearch from './forms/MeasurementTechnique.vue';
import FileSize from './forms/FileSize.vue';

const SEARCH_PARAMS = [
  { name: 'File Size', component: FileSize },
  { name: 'File Type', component: FileType },
  { name: 'Genotype', component: GenotypeSearch },
  { name: 'Species', component: SpeciesSearch },
  { name: 'Measurement Technique', component: MeasurementTechniqueSearch },
];

</script>

<template>
  <v-container class="pa-3">
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
  </v-container>
</template>
