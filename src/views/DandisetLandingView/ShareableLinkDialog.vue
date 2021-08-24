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
        :text="permalink"
        icon-hover-text="Copy permalink to clipboard"
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
import { dandiUrl } from '@/utils/constants';

export default defineComponent({
  name: 'ShareableLinkDialog',
  components: {
    CopyText,
  },
  setup(props, ctx) {
    const store = ctx.root.$store;

    const currentDandiset: ComputedRef<Version> = computed(
      () => store.state.dandiset.publishDandiset,
    );
    const version: ComputedRef<Version> = computed(
      () => store.getters['dandiset/version'],
    );

    const permalink: ComputedRef<string> = computed(() => `${dandiUrl}/dandiset/${currentDandiset.value.dandiset.identifier}/${version.value}`);

    return {
      permalink,
    };
  },
});
</script>
