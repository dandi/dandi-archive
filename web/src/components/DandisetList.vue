<template>
  <v-row>
    <v-list
      two-line
      subheader
    >
      <v-list-item
        v-for="(item, i) in dandisets"
        :key="i"
        selectable
        :to="{ name: 'dandisetLanding', params: { id: item._id } }"
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
          </v-list-item-subtitle>
        </v-list-item-content>
      </v-list-item>
    </v-list>
  </v-row>
</template>

<script>
import moment from 'moment';

import { getDandisetContact } from '@/utils';

export default {
  props: {
    dandisets: {
      // Girder Items
      type: Array,
      required: true,
    },
    dandisetDetails: {
      // nFolders and nItems
      type: Array,
      required: true,
    },
  },
  data() {
    return {

    };
  },
  computed: {
    items() {
      return this.dandisets.map((item, i) => ({ ...item, details: this.dandisetDetails[i] }));
    },
  },
  methods: {
    getDandisetContact,
    formatDate(date) {
      return moment(date).format('LL');
    },
  },
};
</script>
