<template>
  <DandisetsPage
    title="My Dandisets"
    user
  >
    <template #no-content>
      <div v-if="route.query.search">
        No results found in your dandisets.
      </div>
      <div v-else>
        You haven't created any dandisets yet
      </div>
    </template>
  </DandisetsPage>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router';
import DandisetsPage from '@/components/DandisetsPage.vue';

const route = useRoute();
</script>
