<script setup lang="ts">
import { computed } from 'vue';
import { searchParameters } from '../store';

// TODO: fetch initial values dynamically from server?
const range = computed(() => [searchParameters.file_size_min, searchParameters.file_size_max]);

const min = computed<number>(() => range.value[0]);
const max = computed<number>(() => range.value[1]);

function updateFileSizeRange([newMin, newMax]: [number, number]) {
  searchParameters.file_size_min = newMin;
  searchParameters.file_size_max = newMax;
}

</script>

<template>
  <div>
    <v-range-slider
      strict
      min="0"
      max="1000000000000000"
      step="100"
      @value="range"
      @change="updateFileSizeRange"
    />
    <span class="d-flex justify-space-around">
      <v-chip>Min: {{ min }}</v-chip>
      <v-chip>Max: {{ max }}</v-chip>
    </span>
  </div>
</template>
