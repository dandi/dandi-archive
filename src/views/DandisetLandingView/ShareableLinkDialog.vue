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

import { defineComponent, computed } from '@vue/composition-api';

import store from '@/store';
import { dandiUrl } from '@/utils/constants';

export default defineComponent({
  name: 'ShareableLinkDialog',
  components: {
    CopyText,
  },
  setup() {
    const currentDandiset = computed(() => store.state.dandiset.publishDandiset);
    const currentVersion = computed(() => store.getters.version);

    const permalink = computed(() => {
      if (currentDandiset.value?.dandiset && currentVersion.value) {
        return `${dandiUrl}/dandiset/${currentDandiset.value?.dandiset.identifier}/${currentVersion.value}`;
      }
      return '';
    });

    return {
      permalink,
    };
  },
});
</script>
