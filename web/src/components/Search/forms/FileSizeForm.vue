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
        type="number"
        outlined
      />
    </v-col>
    <v-spacer />
    <v-col>
      <span>Max</span>
      <v-text-field
        v-model="searchParameters.file_size_max"
        type="number"
        outlined
      />
    </v-col>
    <v-spacer />
  </v-row>
</template>
