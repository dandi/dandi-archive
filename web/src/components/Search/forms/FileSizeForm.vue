<script setup lang="ts">
import { searchParameters } from '../store';

</script>

<template>
  <!-- Stacked at full width: a byte count such as 1000000000 needs the room. -->
  <v-text-field
    v-model="searchParameters.file_size_min"
    label="Min"
    density="compact"
    type="number"
    min="0"
    variant="outlined"
    hide-details
    class="mb-3"
  />
  <v-text-field
    v-model="searchParameters.file_size_max"
    label="Max"
    density="compact"
    type="number"
    min="0"
    variant="outlined"
    hide-details
  />
</template>
