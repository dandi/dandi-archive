<template>
  <v-menu
    offset-y
    :close-on-content-click="false"
    min-width="420"
    max-width="420"
  >
    <template #activator="{ on }">
      <slot
        name="activator"
        :on="on"
      />
    </template>
    <v-card>
      <CopyText
        class="pa-2"
        :text="citation"
        icon-hover-text="Copy citation to clipboard"
      />
    </v-card>
  </v-menu>
</template>
<script setup lang="ts">
import CopyText from '@/components/CopyText.vue';
import { computed } from 'vue';
import store from '@/store';

const citation = computed(() => store.state.dandiset.dandiset?.metadata?.citation);
</script>
