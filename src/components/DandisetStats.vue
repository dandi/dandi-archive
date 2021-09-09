<template>
  <v-row
    v-if="stats"
    class="align-center text-h6 font-weight-light"
    no-gutters
  >
    <v-col cols="6">
      <v-icon
        class="mr-2"
        color="grey lighten-1"
      >
        mdi-file
      </v-icon>
      <span>{{ stats.asset_count }}</span>
    </v-col>
    <v-col>
      <v-icon
        class="mr-2"
        color="grey lighten-1"
      >
        mdi-server
      </v-icon>
      <span>{{ filesize(stats.size) }}</span>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import {
  defineComponent, computed, ComputedRef,
} from '@vue/composition-api';

import filesize from 'filesize';

import { Version } from '@/types';

interface DandisetStats {
  asset_count: number,
  size: number,
}

export default defineComponent({
  name: 'DandisetStats',
  setup(props, ctx) {
    const store = ctx.root.$store;

    const currentDandiset: ComputedRef<Version> = computed(
      () => store.state.dandiset.publishDandiset,
    );

    const stats: ComputedRef<DandisetStats|null> = computed(() => {
      if (!currentDandiset.value) {
        return null;
      }
      const { asset_count, size } = currentDandiset.value;
      return { asset_count, size };
    });

    return {
      stats,
      filesize,
    };
  },
});
</script>

<style scoped>
.row {
  text-align: center;
  height: 100%;
}
</style>
