<template>
  <v-list
    two-line
    subheader
  >
    <v-list-item
      v-for="(item, i) in items"
      :key="item._id"
      selectable
      :to="{ name: 'dandisetLanding', params: { id: item._id, origin } }"
    >
      <v-row
        no-gutters
        align="center"
      >
        <v-col
          cols="10"
        >
          <v-list-item-content>
            <v-list-item-title>
              <template v-if="item.meta.dandiset.version">
                <v-chip
                  v-if="item.meta.dandiset.version === 'draft'"
                  small
                  color="amber lighten-3"
                  text-color="amber darken-4"
                >
                  <b>DRAFT</b>
                </v-chip>
                <v-chip
                  v-else
                  small
                  color="light-blue lighten-4"
                  text-color="light-blue darken-3"
                >
                  <b>{{ item.meta.dandiset.version }}</b>
                </v-chip>
              </template>
              {{ item.meta.dandiset.name }}
            </v-list-item-title>
            <v-list-item-subtitle>
              Contact <b>{{ getDandisetContact(item) }}</b>
              ·
              Created on <b>{{ formatDate(item.created) }}</b>
              ·
              DANDI:<b>{{ item.meta.dandiset.identifier }}</b>
            </v-list-item-subtitle>
          </v-list-item-content>
        </v-col>
        <template v-if="dandisetStats">
          <v-col
            cols="1"
          >
            <v-icon color="primary">
              mdi-file
            </v-icon>
            {{ dandisetStats[i].items }}
          </v-col>
          <v-col
            cols="1"
          >
            <v-icon color="primary">
              mdi-server
            </v-icon>
            {{ filesize(dandisetStats[i].bytes) }}
          </v-col>
        </template>
      </v-row>
    </v-list-item>
  </v-list>
</template>

<script>
import moment from 'moment';
import filesize from 'filesize';

import { getDandisetContact } from '@/utils';
import girderRest from '@/rest';

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
