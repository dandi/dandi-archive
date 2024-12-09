<template>
  <DandisetsPage title="Search Dandisets" search>
    <template #no-content>
      <div>No results!</div>
      <div>You can search by dandiset name, description, identifier, or contributor name.</div>
    </template>
  </DandisetsPage>
</template>

<script setup lang="ts">
import DandisetsPage from "@/components/DandisetsPage.vue";
</script>
