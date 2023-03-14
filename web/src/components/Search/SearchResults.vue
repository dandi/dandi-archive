<script setup lang="ts">
import { searchResults } from './store';
</script>

<template>
  <v-container>
    <v-card
      v-for="(asset, i) in searchResults"
      :key="`search-result-${i}`"
      class="my-4"
      outlined
    >
      <v-card-text>
        <span
          v-for="([key, value], j) in Object.entries(asset)"
          :key="`search-result-item-${i}-${j}`"
        >
          <b>{{ key }}:</b> {{ value }}
          <br>
        </span>
      </v-card-text>
    </v-card>
  </v-container>
</template>
