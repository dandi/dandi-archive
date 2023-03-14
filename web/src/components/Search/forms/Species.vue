<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { searchParameters } from '../store';
import SPECIES from './species.json';

const searchTerm = ref<string | null>(null);
const options = ref<string[]>([]);
const loading = ref<boolean>(false);

async function populateSpeciesList() {
  loading.value = true;
  // TODO: get species list from server instead
  options.value = await new Promise((resolve) => resolve(SPECIES));
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
