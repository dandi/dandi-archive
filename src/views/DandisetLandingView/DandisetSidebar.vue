<template>
  <div>
    <DandisetActions
      @edit="$emit('edit')"
    />
    <DandisetOwners
      v-if="owners"
      :owners="owners"
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

import { User, Version } from '@/types';

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
    const owners: ComputedRef<User[]> = computed(() => store.state.dandiset.owners);

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
      owners,
      currentVersion,
      otherVersions,
    };
  },
});
</script>
