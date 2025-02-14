<template>
  <DandisetsPage
    title="My Dandisets"
    user
  >
    <template #no-content>
      <div>
        You haven't created any dandisets yet
      </div>
    </template>
  </DandisetsPage>
</template>

<script setup lang="ts">
import DandisetsPage from '@/components/DandisetsPage.vue';
</script>
