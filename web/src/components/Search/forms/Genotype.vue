<script setup lang="ts">
import { ref, watch } from 'vue';
import { searchParameters } from '../store';
import GENOTYPES from './genotypes.json';

const searchTerm = ref<string | null>(null);
const options = ref<string[]>([]);
const loading = ref<boolean>(false);

async function populateGenotypeList(newSearchTerm: string) {
  // TODO: make async call to server to get genotypes.
  // For now, fake the async call and do filtering on client side
  loading.value = true;
  const genotypes: string[] = await new Promise((resolve) => resolve(GENOTYPES));
  options.value = genotypes.filter((g) => g.includes(newSearchTerm));
  loading.value = false;
}

watch(searchTerm, (newSearchTerm) => {
  if (newSearchTerm) {
    populateGenotypeList(newSearchTerm);
  }
});
</script>

<template>
  <v-autocomplete
    v-model="searchParameters.genotype"
    multiple
    clearable
    outlined
    cache-items
    :search-input.sync="searchTerm"
    :items="options"
    :loading="loading"
    label="Genotype(s)"
  />
</template>
