<script setup lang="ts">
import { ref, watch } from "vue";
import { debounce } from "lodash";
import { client } from "@/rest";
import { searchParameters } from "../store";

const searchTerm = ref<string | null>(null);
const options = ref<string[]>([]);
const loading = ref<boolean>(false);
async function populateGenotypeList(newSearchTerm: string) {
  loading.value = true;
  const genotypes: string[] = (
    await client.get("/search/genotypes", { params: { genotype: newSearchTerm } })
  ).data;
  options.value = genotypes.filter((g) => g.includes(newSearchTerm));
  loading.value = false;
}
watch(searchTerm, (newSearchTerm) => {
  if (newSearchTerm) {
    debounce(populateGenotypeList, 500)(newSearchTerm);
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
