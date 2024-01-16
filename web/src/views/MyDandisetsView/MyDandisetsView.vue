<template>
  <DandisetsPage
    title="My Datasets"
    user
  >
    <template #no-content>
      <div>
        You haven't created any datasets yet
      </div>
    </template>
  </DandisetsPage>
</template>

<script setup lang="ts">
import DandisetsPage from '@/components/DandisetsPage.vue';
</script>
