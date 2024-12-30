<template>
  <DandisetsPage
    title="Starred Dandisets"
    starred
  >
    <template #empty>
      <v-alert
        type="info"
        text
      >
        You haven't starred any Dandisets yet.
      </v-alert>
    </template>
  </DandisetsPage>
</template>

<script setup lang="ts">
import DandisetsPage from '@/components/DandisetsPage.vue';
</script>
