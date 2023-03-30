<script setup lang="ts">
import { searchResults, loading } from './store';
</script>

<template>
  <v-container>
    <v-skeleton-loader
      v-if="loading"
      class="mx-auto"
      type="image"
    />
    <v-card
      v-for="(asset, i) in searchResults"
      v-else
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
