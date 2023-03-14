<script setup lang="ts">
import SearchParameters from '@/components/Search/SearchParameters.vue';
import SearchResults from '@/components/Search/SearchResults.vue';
</script>

<template>
  <v-container fluid>
    <v-row no-gutters>
      <v-col cols="3">
        <span class="text-h4">Search Assets</span>
        <v-sheet class="ma-2 pa-2">
          <SearchParameters />
        </v-sheet>
      </v-col>
      <v-col cols="9">
        <span class="text-h4">Results</span>
        <v-sheet class="ma-2 pa-2">
          <SearchResults />
        </v-sheet>
      </v-col>
    </v-row>
  </v-container>
</template>
