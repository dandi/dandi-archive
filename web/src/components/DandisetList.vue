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

<script>
import moment from 'moment';
import filesize from 'filesize';

import { getDandisetContact } from '@/utils';
import toggles from '@/featureToggle';
import { girderRest } from '@/rest';

export default {
  props: {
    dandisets: {
      // Girder Items
      type: Array,
      required: true,
    },
  },
  computed: {
    items() {
      return this.dandisets;
    },
    origin() {
      const { name, params, query } = this.$route;
      return { name, params, query };
    },
  },
  asyncComputed: {
    async dandisetStats() {
      if (toggles.DJANGO_API) {
        return this.dandisets;
      }
      const { items } = this;
      return Promise.all(items.map(async (item) => {
        const { identifier } = item.meta.dandiset;
        const { data } = await girderRest.get(`/dandi/${identifier}/stats`);
        return data;
      }));
    },
  },
  methods: {
    filesize,
    getDandisetContact,
    formatDate(date) {
      return moment(date).format('LL');
    },
  },
};
</script>
