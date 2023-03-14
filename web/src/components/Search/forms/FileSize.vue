<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import { searchParameters } from '../store';

// TODO: fetch initial values dynamically from server?
const range = ref<[number, number]>([0, 1000000]);

const min = computed<number>(() => range.value[0]);
const max = computed<number>(() => range.value[1]);

watch(range, ([newMin, newMax]) => {
  searchParameters.file_type_min = newMin;
  searchParameters.file_type_max = newMax;
});

</script>

<template>
  <div>
    <v-range-slider
      v-model="range"
      label="Min/max file size"
      :hint="`Min: ${min}\tMax:${max}`"
      strict
      min="0"
      max="1000000"
      step="100"
    />
    <!-- <span class="d-flex justify-space-around">
      <v-chip>Min: {{ min }}</v-chip>
      <v-chip>Max: {{ max }}</v-chip>
    </span> -->
  </div>
</template>
