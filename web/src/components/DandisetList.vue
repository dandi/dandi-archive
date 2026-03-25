<template>
  <v-list
    lines="three"
    class="pb-8"
  >
    <v-list-item
      v-for="(item, index) in dandisets"
      :key="item.dandiset.identifier"
      class="py-3"
      :to="{
        name: 'dandisetLanding',
        params: { identifier: item.dandiset.identifier },
        query: { ...$route.query, pos: getPos(index) },
      }"
      exact
    >
      <v-list-item-title class="wrap-text text-h6 text-grey-darken-3 font-weight-medium">
        {{ item.name }}
        <StarButton
          :identifier="item.dandiset.identifier"
          :initial-star-count="item.dandiset.star_count"
          :initial-is-starred="item.dandiset.is_starred"
          class="float-right"
        />
      </v-list-item-title>
      <v-list-item-subtitle class="opacity-70">
        <v-chip
          v-if="item.version && item.version !== 'draft'"
          class="mr-1 bg-light-blue-lighten-4 text-light-blue-darken-3"
          size="small"
          variant="flat"
        >
          <b>{{ item.version }}</b>
        </v-chip>
        <v-chip
          v-else
          size="x-small"
          class="mr-1 px-2 bg-amber-lighten-3 text-amber-darken-4"
        >
          <b>DRAFT</b>
        </v-chip>
        <v-chip
          v-if="item.dandiset.embargo_status !== 'OPEN'"
          size="x-small"
          class="mr-1 px-2"
          :color="`bg-${item.dandiset.embargo_status === 'EMBARGOED' ? 'red' : 'green'} lighten-4 text-${item.dandiset.embargo_status === 'EMBARGOED' ? 'red' : 'green'}-darken-3`"
        >
          <b>{{ item.dandiset.embargo_status }}</b>
        </v-chip>

        {{ archiveName }}:<b>{{ item.dandiset.identifier }}</b>
        ·
        Contact <b>{{ item.dandiset.contact_person }}</b>
        ·
        Updated on <b>{{ formatDate(item.modified) }}</b>
        ·
        <template v-if="dandisets">
          <v-icon
            size="small"
            class="pb-1"
          >
            mdi-file
          </v-icon>
          {{ item.asset_count }}
          ·
          <v-icon
            size="small"
            class="pb-1"
          >
            mdi-database
          </v-icon>
          {{ filesize(item.size, { round: 1, base: 10, standard: 'iec' }) }}
        </template>
      </v-list-item-subtitle>

      <slot :name="item.dandiset.identifier" />
    </v-list-item>
  </v-list>
</template>

<script setup lang="ts">
import { ref, onMounted, type PropType } from 'vue';
import { useRoute } from 'vue-router';
import moment from 'moment';
import { filesize } from 'filesize';
import StarButton from '@/components/StarButton.vue';
import { dandiRest } from '@/rest';

import type { Version } from '@/types';
import { DANDISETS_PER_PAGE } from '@/utils/constants';

defineProps({
  dandisets: {
    type: Array as PropType<Version[]>,
    required: true,
  },
});

const route = useRoute();
const archiveName = ref<string>('');

onMounted(async () => {
  const info = await dandiRest.info();
  archiveName.value = info.instance_config.instance_name;
});

// current position in search result set = items on prev pages + position on current page
function getPos(index: number) {
  return (Number(route.query.page || 1) - 1) * DANDISETS_PER_PAGE + (index + 1);
}
function formatDate(date: string) {
  return moment(date).format('LL');
}
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
