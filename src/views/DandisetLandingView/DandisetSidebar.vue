<template>
  <div>
    <DandisetActions
      @edit="$emit('edit')"
    />
    <DandisetOwners
      :user-can-modify-dandiset="userCanModifyDandiset"
    />
    <DandisetPublish
      :user-can-modify-dandiset="userCanModifyDandiset"
      @edit="$emit('edit')"
    />
  </div>
</template>

<script lang="ts">
import {
  defineComponent, computed,
} from '@vue/composition-api';

import store from '@/store';
import { Version } from '@/types';

import DandisetActions from './DandisetActions.vue';
import DandisetOwners from './DandisetOwners.vue';
import DandisetPublish from './DandisetPublish.vue';

export default defineComponent({
  name: 'DandisetSidebar',
  components: {
    DandisetActions,
    DandisetOwners,
    DandisetPublish,
  },
  props: {
    userCanModifyDandiset: {
      type: Boolean,
      required: true,
    },
  },
  setup() {
    const currentDandiset = computed(() => store.state.dandiset.dandiset);
    const currentVersion = computed(() => store.getters.dandiset.version);

    const otherVersions = computed(() => store.state.dandiset.versions?.filter(
      (version: Version) => version.version !== currentVersion.value,
    ));

    return {
      currentDandiset,
      currentVersion,
      otherVersions,
    };
  },
});
</script>
