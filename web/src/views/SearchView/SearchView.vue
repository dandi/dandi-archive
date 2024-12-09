<script setup lang="ts">
import SearchParameters from "@/components/Search/SearchParameters.vue";
import SearchResults from "@/components/Search/SearchResults.vue";
</script>

<template>
  <v-container fluid>
    <v-row no-gutters>
      <v-col md="3" sm="12">
        <SearchParameters />
      </v-col>
      <v-col md="9" sm="12">
        <SearchResults />
      </v-col>
    </v-row>
  </v-container>
</template>
