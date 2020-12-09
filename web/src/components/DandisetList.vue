<template>
  <v-list
    two-line
    subheader
  >
    <v-list-item
      v-for="(item, i) in items"
      :key="item._id"
      selectable
      :to="{
        name: 'dandisetLanding',
        params: { identifier: item.meta.dandiset.identifier, origin }
      }"
    >
      <v-row
        no-gutters
        align="center"
      >
        <v-col cols="10">
          <v-list-item-content>
            <v-list-item-title>
              {{ item.meta.dandiset.name }}
            </v-list-item-title>
            <v-list-item-subtitle>
              <v-chip
                v-if="item.version && item.version !== 'draft'"
                small
                color="light-blue lighten-4"
                text-color="light-blue darken-3"
              >
                <b>{{ item.version }}</b>
              </v-chip>
              <v-chip
                v-else
                small
                color="amber lighten-3"
                text-color="amber darken-4"
              >
                <b>DRAFT</b>
              </v-chip>
              DANDI:<b>{{ item.meta.dandiset.identifier }}</b>
              ·
              Contact <b>{{ getDandisetContact(item) }}</b>
              ·
              Updated on <b>{{ formatDate(item.updated) }}</b>
              ·
              <template v-if="dandisetStats">
                <v-icon
                  small
                  class="pb-1"
                >
                  mdi-file
                </v-icon>
                {{ dandisetStats[i].items }}
                ·
                <v-icon
                  small
                  class="pb-1"
                >
                  mdi-database
                </v-icon>
                {{ filesize(dandisetStats[i].bytes) }}
              </template>
            </v-list-item-subtitle>
          </v-list-item-content>
        </v-col>
      </v-row>
    </v-list-item>
  </v-list>
</template>

<script lang="ts">
import {
  defineComponent, ref, computed, watch, PropType,
} from '@vue/composition-api';
import moment from 'moment';
import filesize from 'filesize';

import { getDandisetContact } from '@/utils';
import toggles from '@/featureToggle';
import { girderRest } from '@/rest';

type Dandiset = {};
interface DandisetStats {
  bytes: number;
  folders: number;
  items: number;
}

export default defineComponent({
  name: 'DandisetList',
  props: {
    dandisets: {
      // Girder Items
      type: Array as PropType<Dandiset[]>,
      required: true,
    },
  },
  setup(props, ctx) {
    // Will be replaced by `useRoute` if vue-router is upgraded to vue-router@next
    // https://next.router.vuejs.org/api/#useroute
    const route = ctx.root.$route;

    const origin = computed(() => {
      const { name, params, query } = route;
      return { name, params, query };
    });

    const items = computed(() => props.dandisets);
    const dandisetStats = ref<DandisetStats[] | null>(null);
    async function fetchDandisetStats(dandisets: Dandiset[]) {
      // Set back to null in case of failure
      dandisetStats.value = null;

      if (toggles.DJANGO_API) {
        dandisetStats.value = dandisets as DandisetStats[];
      }

      const res = await Promise.all(dandisets.map(async (dandiset: any) => {
        const { identifier } = dandiset.meta.dandiset;
        const { data } = await girderRest.get(`/dandi/${identifier}/stats`);
        return data;
      }));

      dandisetStats.value = res;
    }

    // Fetching dandiset stats must be done this way since we don't have access to asyncComputed
    watch(() => props.dandisets, fetchDandisetStats, { immediate: true });

    function formatDate(date: string) {
      return moment(date).format('LL');
    }

    return {
      origin,
      items,
      dandisetStats,
      formatDate,

      // Returned imports
      filesize,
      getDandisetContact,
    };
  },
});
</script>
