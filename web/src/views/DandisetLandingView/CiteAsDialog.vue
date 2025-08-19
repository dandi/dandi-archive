<template>
  <v-menu
    :close-on-content-click="false"
    min-width="420"
    max-width="420"
  >
    <template #activator="{ props }">
      <v-list-item
        id="cite_as"
        class="justify-space-between border border-b-0"
        v-bind="props"
      >
        <template #prepend>
          <v-icon
            color="primary"
            start
          >
            mdi-format-quote-close
          </v-icon>
          <v-list-item-title>Cite As</v-list-item-title>
        </template>
        <template #append>
          <v-icon end>
            mdi-chevron-down
          </v-icon>
        </template>
      </v-list-item>
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
import { useDandisetStore } from '@/stores/dandiset';

const store = useDandisetStore();

const citation = computed(() => store.dandiset?.metadata?.citation);
</script>
