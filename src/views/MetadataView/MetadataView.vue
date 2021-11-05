<template>
  <div
    v-if="schema && Object.entries(meta).length"
    v-page-title="meta.name"
  >
    <meditor
      :schema="schema"
      :model="meta"
      :readonly="!userCanModifyDandiset"
      @close="edit = false"
    />
  </div>
</template>

<script lang="ts">
import {
  defineComponent, computed,
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

    if (!currentDandiset.value) {
      const { identifier, version } = props;
      store.dispatch.dandiset.fetchDandiset({ identifier, version });
    }

    return {
      schema,
      meta,
      userCanModifyDandiset,
    };
  },
});
</script>
