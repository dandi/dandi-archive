<script setup lang="ts">
import { searchParameters } from '../store';

</script>

<template>
  <v-row>
    <v-spacer />
    <v-col>
      <span>Min</span>
      <v-text-field
        v-model="searchParameters.file_size_min"
        density="compact"
        type="number"
        variant="outlined"
        style="min-width: 4ch;"
      />
    </v-col>
    <v-spacer />
    <v-col>
      <span>Max</span>
      <v-text-field
        v-model="searchParameters.file_size_max"
        density="compact"
        type="number"
        variant="outlined"
        style="min-width: 4ch;"
      />
    </v-col>
    <v-spacer />
  </v-row>
</template>
