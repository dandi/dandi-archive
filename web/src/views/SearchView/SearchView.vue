<script setup lang="ts">
import SearchParameters from '@/components/Search/SearchParameters.vue';
import SearchResults from '@/components/Search/SearchResults.vue';
</script>

<template>
  <v-container fluid>
    <v-row no-gutters>
      <v-col cols="3">
        <SearchParameters />
      </v-col>
      <v-col cols="9">
        <SearchResults />
      </v-col>
    </v-row>
  </v-container>
</template>
