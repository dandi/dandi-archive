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
<script lang="ts">
import CopyText from '@/components/CopyText.vue';

import {
  defineComponent, computed, ComputedRef,
} from '@vue/composition-api';

import { Version } from '@/types';

export default defineComponent({
  name: 'CiteAsDialog',
  components: {
    CopyText,
  },
  setup(props, ctx) {
    const store = ctx.root.$store;

    const currentDandiset: ComputedRef<Version> = computed(
      () => store.state.dandiset.publishDandiset,
    );

    const citation: ComputedRef<string> = computed(() => currentDandiset.value.metadata.citation);

    return {
      citation,
    };
  },
});
</script>
