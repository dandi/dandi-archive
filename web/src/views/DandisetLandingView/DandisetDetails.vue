<template>
  <v-card
    v-if="currentDandiset"
    height="100%"
    class="px-3 py-1"
  >
    <template>
      <v-row
        v-if="contactName"
        no-gutters
        :class="rowClasses"
      >
        <v-icon>mdi-account</v-icon>
        <span :class="labelClasses">Contact</span>
        <span :class="itemClasses">{{ contactName }}</span>
      </v-row>
      <v-row
        no-gutters
        :class="rowClasses"
      >
        <v-icon>mdi-calendar</v-icon>
        <span :class="labelClasses">Created on</span>
        <span :class="itemClasses">{{ created }}</span>
      </v-row>
      <v-row
        no-gutters
        :class="rowClasses"
      >
        <v-icon>mdi-update</v-icon>
        <span :class="labelClasses">Last updated</span>
        <span :class="itemClasses">{{ lastUpdated }}</span>
      </v-row>

      <v-divider class="my-2" />

      <v-row :class="`${rowClasses} px-2`">
        <span :class="labelClasses">Identifier</span>
        <span :class="itemClasses">{{ currentDandiset.meta.dandiset.identifier }}</span>
      </v-row>

      <v-divider class="my-2 px-0 mx-0" />

      <v-row>
        <v-col>
          <v-card
            color="grey lighten-3"
            class="mx-2"
            flat
            tile
          >
            <v-row
              no-gutters
              class="py-2"
            >
              <v-col cols="11">
                <v-icon
                  class="mx-2"
                  color="primary"
                >
                  mdi-link
                </v-icon>
                <span :class="itemClasses">Draft</span>
              </v-col>
              <v-col>
                <v-tooltip top>
                  <template v-slot:activator="{ on }">
                    <v-icon
                      small
                      color="grey darken-1"
                      v-on="on"
                    >
                      mdi-help-circle
                    </v-icon>
                  </template>
                  <span>This is a version of your dandiset that contains unpublished changes.</span>
                </v-tooltip>
              </v-col>
            </v-row>
          </v-card>
        </v-col>
      </v-row>
      <v-row>
        <v-col class="pa-0">
          <v-card
            color="grey lighten-2"
            tile
            flat
          >
            <div class="py-1 px-3">
              Versions
            </div>
          </v-card>
        </v-col>
      </v-row>

      <v-row>
        <v-timeline dense>
          <v-timeline-item
            v-for="(version, i) in versions"
            :key="version.version || 'draft'"
            small
            right
            :color="timelineVersionItemColor(i)"
          >
            <v-btn
              text
              class="font-weight-medium"
              @click="setVersion(i)"
            >
              {{ version.version || 'DRAFT' }}
            </v-btn>
          </v-timeline-item>
        </v-timeline>
      </v-row>
    </template>
  </v-card>
</template>

<script>
import { mapState } from 'vuex';
import moment from 'moment';

import { publishRest } from '@/rest';


export default {
  name: 'DandisetDetails',
  data() {
    return {
      rowClasses: 'my-1',
      labelClasses: 'mx-2 text--secondary',
      itemClasses: 'font-weight-medium',
      currentVersionIndex: 0,
    };
  },
  computed: {
    created() {
      return this.formatDateTime(this.currentDandiset.created);
    },
    lastUpdated() {
      return this.formatDateTime(this.currentDandiset.updated);
    },
    contactName() {
      if (!this.currentDandiset || !this.currentDandiset.meta.dandiset.contributors) {
        return null;
      }

      const contacts = this.currentDandiset.meta.dandiset.contributors.filter(
        (contributor) => contributor.roles.includes('ContactPerson'),
      );

      if (contacts.length > 0) {
        return contacts[0].name;
      }

      return null;
    },
    currentDandiset() {
      // Done this way because we'll want to add in
      // fetching stats from the publish endpoint later on.
      return this.girderDandiset;
    },
    // currentVersionIndex() {
    //   if (!this.publishDandiset) {
    //     return 0;
    //   }

    //   const index = this.versions.findIndex((version) => this.publishDandiset.version === version);
    //   return index === -1 ? 0 : index;
    // },
    ...mapState('girder', {
      girderDandiset: (state) => state.girderDandiset,
    }),
    ...mapState('publish', {
      publishDandiset: (state) => state.publishDandiset,
    }),
  },
  asyncComputed: {
    async versions() {
      const { identifier } = this.girderDandiset.meta.dandiset;

      try {
        const { results } = await publishRest.versions(identifier);
        return [
          // First entry is null as it represents the draft dandiset
          { version: null },
          ...results,
        ];
      } catch (err) {
        return [];
      }
    },
  },
  watch: {
    publishDandiset(val) {
      // TODO: Figure out why the computed version of this doesn't work
      if (!val) {
        this.currentVersionIndex = 0;
        return;
      }

      const index = this.versions.findIndex(({ version }) => val.version === version);
      this.currentVersionIndex = index === -1 ? 0 : index;
    },
  },
  methods: {
    setVersion(index) {
      const { version } = this.versions[index];

      if (version) {
        this.$store.dispatch('publish/fetchPublishDandiset', {
          version,
          girderId: this.girderDandiset._id,
          identifier: this.girderDandiset.meta.dandiset.identifier,
        });
      } else {
        this.$store.commit('publish/setPublishDandiset', null);
      }
    },
    formatDateTime(datetimeStr) {
      const datetime = moment(datetimeStr);
      const date = datetime.format('LL');
      const time = datetime.format('hh:mm A');

      return `${date} at ${time}`;
    },
    timelineVersionItemColor(index) {
      if (this.currentVersionIndex !== index) { return 'grey'; }
      if (this.versions[index].version === null) {
        return 'amber darken-4';
      }

      return 'primary';
    },
  },
};
</script>
