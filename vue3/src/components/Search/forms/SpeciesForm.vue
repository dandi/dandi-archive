<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { client } from '@/rest';
import { searchParameters } from '../store';

const searchTerm = ref<string | null>(null);
const options = ref<string[]>([]);
const loading = ref<boolean>(false);
async function populateSpeciesList(newSearchTerm: string = '') {
  loading.value = true;
  const species: string[] = (await client.get('/search/species', { params: { species: newSearchTerm } })).data;
  options.value = species;
  loading.value = false;
}
onMounted(populateSpeciesList);
</script>

<template>
  <v-autocomplete
    v-model="searchParameters.species"
    multiple
    clearable
    outlined
    cache-items
    :search-input.sync="searchTerm"
    :items="options"
    :loading="loading"
    label="Species"
  />
</template>
