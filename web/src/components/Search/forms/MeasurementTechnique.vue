<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { searchParameters } from '../store';
import MEASUREMENT_TECHNIQUES from './measurementTechniques.json';

const searchTerm = ref<string | null>(null);
const options = ref<string[]>([]);
const loading = ref<boolean>(false);

async function populateMeasurementTechniqueList() {
  loading.value = true;
  // TODO: get list from server instead
  options.value = await new Promise((resolve) => resolve(MEASUREMENT_TECHNIQUES));
  loading.value = false;
}

onMounted(populateMeasurementTechniqueList);
</script>

<template>
  <v-autocomplete
    v-model="searchParameters.measurement_technique"
    multiple
    clearable
    outlined
    cache-items
    :search-input.sync="searchTerm"
    :items="options"
    :loading="loading"
    label="Measurement Technique(s)"
  />
</template>
