<template>
  <div
    v-if="schema && Object.entries(meta).length"
    v-page-title="meta.name"
  >
    <meditor
      v-if="renderMeditor"
      :schema="schema"
      :model="meta"
      :readonly="!userCanModifyDandiset"
      @close="edit = false"
    />
  </div>
</template>

<script lang="ts">
import {
  defineComponent, computed, watchEffect, ref,
} from '@vue/composition-api';

import store from '@/store';

import Meditor from './Meditor.vue';

export default defineComponent({
  name: 'MetadataView',
  components: { Meditor },
  props: {
    identifier: {
      type: String,
      required: true,
    },
    version: {
      type: String,
      required: true,
    },
  },
  setup(props) {
    const currentDandiset = computed(() => store.state.dandiset.dandiset);
    const schema = computed(() => store.state.dandiset.schema);
    const meta = computed(() => (currentDandiset.value ? currentDandiset.value.metadata : {}));
    const userCanModifyDandiset = computed(() => store.getters.dandiset.userCanModifyDandiset);

    const renderMeditor = ref(true);

    watchEffect(async () => {
      if (
        !currentDandiset.value
      || currentDandiset.value.dandiset.identifier !== props.identifier
      || currentDandiset.value.version !== props.version) {
        // force vjsf to rerender the meditor
        renderMeditor.value = false;

        const { identifier, version } = props;
        await store.dispatch.dandiset.fetchDandiset({ identifier, version });

        renderMeditor.value = true;
      }
    });

    return {
      schema,
      meta,
      userCanModifyDandiset,
      renderMeditor,
    };
  },
});
</script>
