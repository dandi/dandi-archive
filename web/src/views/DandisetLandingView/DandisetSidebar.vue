<template>
  <div
    v-if="currentDandiset"
    class="border-s"
  >
    <template v-if="!hideActions">
      <DandisetActions />
      <v-divider />
    </template>
    <DandisetOwners
      :user-can-modify-dandiset="userCanModifyDandiset"
    />
    <v-divider />
    <div v-if="currentDandiset.dandiset.embargo_status === 'EMBARGOED'">
      <DandisetUnembargo />
    </div>
    <div v-else>
      <DandisetPublish
        :user-can-modify-dandiset="userCanModifyDandiset"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

import { useDandisetStore } from '@/stores/dandiset';

import DandisetActions from './DandisetActions.vue';
import DandisetOwners from './DandisetOwners.vue';
import DandisetPublish from './DandisetPublish.vue';
import DandisetUnembargo from './DandisetUnembargo.vue';

defineProps({
  userCanModifyDandiset: {
    type: Boolean,
    required: true,
  },
  // On small screens the actions are shown above the tabs instead (see DandisetMain).
  hideActions: {
    type: Boolean,
    default: false,
  },
})

const store = useDandisetStore();

const currentDandiset = computed(() => store.dandiset);
</script>
