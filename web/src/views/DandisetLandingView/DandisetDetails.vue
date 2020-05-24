<template>
  <v-card
    v-if="currentDandiset"
    height="100%"
    class="px-3 py-1"
  >
    <template>
      <v-row
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
            </v-row>
          </v-card>
        </v-col>
      </v-row>
      <!-- TODO: Uncomment this once the versions API is accessible -->
      <!-- <v-row>
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
        <v-timeline>
          <v-timeline-item
            small
            right
          >
            <template v-slot:opposite>
              <span class="caption text--secondary">
                02/26/19
              </span>
            </template>

            <span class="font-weight-medium">
              1.2.1
            </span>
          </v-timeline-item>
        </v-timeline>
      </v-row> -->
    </template>
  </v-card>
</template>

<script>
import filesize from 'filesize';
import { mapState } from 'vuex';
import moment from 'moment';


export default {
  name: 'DandisetDetails',
  data() {
    return {
      rowClasses: 'my-1',
      labelClasses: 'mx-2 text--secondary',
      itemClasses: 'font-weight-medium',
    };
  },
  computed: {
    computedSize() {
      if (!this.currentDandiset || !this.currentDandiset.size) return null;
      return filesize(this.currentDandiset.size);
    },
    created() {
      return this.formatDateTime(this.currentDandiset.created);
    },
    lastUpdated() {
      return this.formatDateTime(this.currentDandiset.updated);
    },
    contactName() {
      if (!this.currentDandiset) {
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
    ...mapState('girder', {
      currentDandiset: (state) => state.currentDandiset,
    }),
  },
  methods: {
    formatDateTime(datetimeStr) {
      const datetime = moment(datetimeStr);
      const date = datetime.format('LL');
      const time = datetime.format('hh:mm A');

      return `${date} at ${time}`;
    },
  },
};
</script>
