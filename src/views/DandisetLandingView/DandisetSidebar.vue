<template>
  <div>
    <DandisetActions
      @edit="$emit('edit')"
    />
    <DandisetOwners
      v-if="userCanModifyDandiset"
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
  defineComponent, computed, ComputedRef,
} from '@vue/composition-api';

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
  setup(props, ctx) {
    const store = ctx.root.$store;

    const currentDandiset: ComputedRef<Version> = computed(
      () => store.state.dandiset.publishDandiset,
    );

    const currentVersion: ComputedRef<string> = computed(
      () => store.getters['dandiset/version'],
    );

    const otherVersions: ComputedRef<Version[]> = computed(
      () => store.state.dandiset.versions.filter(
        (version: Version) => version.version !== currentVersion.value,
      ),
    );

    return {
      currentDandiset,
      currentVersion,
      otherVersions,
    };
  },
});
</script>
