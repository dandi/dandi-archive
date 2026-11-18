<template>
  <div class="mt-8">
    <div class="d-flex align-center mb-1">
      <span class="text-h5">{{ title }}</span>
      <v-chip
        size="small"
        variant="outlined"
        color="grey-darken-1"
        class="ml-3"
      >
        Optional
      </v-chip>
    </div>
    <div class="text-body-2 mb-3">
      <slot name="description" />
    </div>
    <slot />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string;
}>();
</script>
