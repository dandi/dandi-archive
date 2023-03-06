<template>
  <v-list
    three-line
    subheader
  >
    <v-list-item
      v-for="(item, index) in dandisets"
      :key="item.dandiset.identifier"
      selectable
      :to="{
        name: 'dandisetLanding',
        params: { identifier: item.dandiset.identifier, origin },
        query: { ...$route.query, pos: getPos(index) },
      }"
      exact
    >
      <v-list-item-content>
        <v-list-item-title class="wrap-text text-h6 grey--text text--darken-3 pb-1">
          {{ item.name }}
        </v-list-item-title>
        <v-list-item-subtitle>
          <v-chip
            v-if="item.version && item.version !== 'draft'"
            class="mr-1"
            small
            color="light-blue lighten-4"
            text-color="light-blue darken-3"
          >
            <b>{{ item.version }}</b>
          </v-chip>
          <v-chip
            v-else
            x-small
            class="mr-1 px-2"
            color="amber lighten-3"
            text-color="amber darken-4"
          >
            <b>DRAFT</b>
          </v-chip>
          <v-chip
            v-if="item.dandiset.embargo_status !== 'OPEN'"
            x-small
            class="mr-1 px-2"
            :color="`${item.dandiset.embargo_status === 'EMBARGOED' ? 'red' : 'green'} lighten-4`"
            :text-color="
              `${item.dandiset.embargo_status === 'EMBARGOED' ? 'red' : 'green'} darken-3`
            "
          >
            <b>{{ item.dandiset.embargo_status }}</b>
          </v-chip>

          DANDI:<b>{{ item.dandiset.identifier }}</b>
          ·
          Contact <b>{{ item.dandiset.contact_person }}</b>
          ·
          Updated on <b>{{ formatDate(item.modified) }}</b>
          ·
          <template v-if="dandisets">
            <v-icon
              small
              class="pb-1"
            >
              mdi-file
            </v-icon>
            {{ item.asset_count }}
            ·
            <v-icon
              small
              class="pb-1"
            >
              mdi-database
            </v-icon>
            {{ filesize(item.size, { round: 1, base: 10, standard: 'iec' }) }}
          </template>
        </v-list-item-subtitle>
      </v-list-item-content>
    </v-list-item>
  </v-list>
</template>

<script lang="ts">
import type { PropType } from 'vue';
import { defineComponent, computed } from 'vue';
import { useRoute } from 'vue-router/composables';
import moment from 'moment';
import filesize from 'filesize';

import type { Version } from '@/types';
import { DANDISETS_PER_PAGE } from '@/utils/constants';

export default defineComponent({
  name: 'DandisetList',
  props: {
    dandisets: {
      type: Array as PropType<Version[]>,
      required: true,
    },
  },
  setup() {
    const route = useRoute();

    const origin = computed(() => {
      const { name, params, query } = route;
      return { name, params, query };
    });
    // current position in search result set = items on prev pages + position on current page
    function getPos(index: number) {
      return (Number(route.query.page || 1) - 1) * DANDISETS_PER_PAGE + (index + 1);
    }
    function formatDate(date: string) {
      return moment(date).format('LL');
    }

    return {
      origin,
      formatDate,
      getPos,
      // Returned imports
      filesize,
    };
  },
});
</script>

<style scoped>
.wrap-text {
  -webkit-line-clamp: unset !important;
}
.v-list-item__title {
  white-space: normal;
}

.v-list-item {
  border-bottom: 1px solid #eee;
}

.v-list--three-line .v-list-item .v-list-item__content,
.v-list-item--three-line .v-list-item__content {
  align-self: center;
}
</style>
