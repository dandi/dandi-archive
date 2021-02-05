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

      <template v-if="stats">
        <v-row :class="`${rowClasses} px-2`">
          <v-col
            cols="auto"
            class="text--secondary mx-2 pa-0 py-1"
          >
            <v-icon color="primary">
              mdi-file
            </v-icon>
            {{ stats.items }}
          </v-col>
          <v-col
            v-if="!DJANGO_API"
            class="text--secondary mx-2 pa-0 py-1"
            cols="auto"
          >
            <v-icon color="primary">
              mdi-folder
            </v-icon>
            {{ stats.folders }}
          </v-col>
          <v-col
            class="text--secondary mx-2 pa-0 py-1"
            cols="auto"
          >
            <v-icon color="primary">
              mdi-server
            </v-icon>
            {{ formattedSize }}
          </v-col>
        </v-row>
      </template>

      <v-divider class="mt-2 px-0 mx-0" />

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
                  mdi-source-branch
                </v-icon>
                <span :class="`${itemClasses} text-capitalize`"> {{ currentVersion }} </span>
              </v-col>
              <v-col v-if="draftDandiset">
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

      <v-divider class="my-2 px-0 mx-0" />

      <v-row
        no-gutters
        :class="rowClasses"
      >
        <v-col>
          <span :class="labelClasses">Ownership</span>
        </v-col>
        <v-col cols="auto">
          <v-dialog
            v-model="ownerDialog"
            width="50%"
          >
            <template v-slot:activator="{ on }">
              <v-tooltip
                :disabled="!manageOwnersDisabled"
                left
              >
                <template v-slot:activator="{ on: tooltipOn }">
                  <div v-on="tooltipOn">
                    <v-btn
                      color="primary"
                      x-small
                      text
                      :disabled="manageOwnersDisabled"
                      v-on="on"
                    >
                      <v-icon
                        x-small
                        class="pr-1"
                      >
                        mdi-lock
                      </v-icon>
                      Manage
                    </v-btn>
                  </div>
                </template>
                <template v-if="loggedIn">
                  You must be an owner to manage ownership.
                </template>
                <template v-else>
                  You must be logged in to manage ownership.
                </template>
              </v-tooltip>
            </template>
            <DandisetOwnersDialog
              :key="ownerDialogKey"
              :owners="owners"
              @close="ownerDialog = false"
            />
          </v-dialog>
        </v-col>
      </v-row>

      <!-- TODO: Make chips wrap, instead of pushing whole card wide -->
      <v-row :class="rowClasses">
        <v-col cols="12">
          <v-chip
            v-for="owner in limitedOwners"
            :key="owner.id /* TODO remove this */ || owner.username"
            color="light-blue lighten-4"
            text-color="light-blue darken-3"
            class="font-weight-medium ma-1"
          >
            {{ owner.login /* TODO remove this */ || owner.username }}
          </v-chip>
          <span
            v-if="numExtraOwners"
            class="ml-1 text--secondary"
          >
            +{{ numExtraOwners }} more...
          </span>
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
            v-for="version in versions"
            :key="version.version"
            small
            right
            :color="timelineVersionItemColor(version)"
          >
            <v-btn
              text
              class="font-weight-medium"
              @click="setVersion(version)"
            >
              {{ version.version }}
            </v-btn>
          </v-timeline-item>
        </v-timeline>
      </v-row>
    </template>
  </v-card>
</template>

<script>
import { mapState, mapGetters } from 'vuex';
import { loggedIn, user, girderRest } from '@/rest';
import moment from 'moment';
import filesize from 'filesize';

import toggles from '@/featureToggle';
import { draftVersion } from '@/utils/constants';
import DandisetOwnersDialog from './DandisetOwnersDialog.vue';

export default {
  name: 'DandisetDetails',
  components: {
    DandisetOwnersDialog,
  },
  data() {
    return {
      rowClasses: 'my-1',
      labelClasses: 'mx-2 text--secondary',
      itemClasses: 'font-weight-medium',
      ownerDialog: false,
      ownerDialogKey: 0,
    };
  },
  computed: {
    user,
    loggedIn,
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
      if (toggles.DJANGO_API) {
        return this.publishDandiset;
      }
      return this.girderDandiset;
    },
    draftDandiset() {
      return this.currentVersion === draftVersion;
    },
    manageOwnersDisabled() {
      if (!this.loggedIn || !this.owners) return true;
      return !this.owners.find((owner) => owner.id === this.user._id);
    },
    limitedOwners() {
      if (!this.owners) return [];
      return this.owners.slice(0, 5);
    },
    numExtraOwners() {
      if (!this.owners) return 0;
      return this.owners.length - this.limitedOwners.length;
    },
    formattedSize() {
      const { stats } = this;
      if (!stats) {
        return undefined;
      }
      return filesize(stats.bytes);
    },
    versions() {
      if (toggles.DJANGO_API) {
        return this.publishedVersions || [];
      }
      // Girder only has the draft version
      return [{ version: draftVersion }];
    },
    ...mapState('dandiset', {
      girderDandiset: (state) => state.girderDandiset,
      publishDandiset: (state) => state.publishDandiset,
      owners: (state) => state.owners,
      publishedVersions: (state) => state.versions,
    }),
    ...mapGetters('dandiset', {
      currentVersion: 'version',
    }),
  },
  asyncComputed: {
    async stats() {
      if (toggles.DJANGO_API) {
        const { items, bytes } = this.currentDandiset;
        return { items, bytes };
      }
      const { identifier } = this.currentDandiset.meta.dandiset;
      const { data } = await girderRest.get(`/dandi/${identifier}/stats`);
      return data;
    },
  },
  watch: {
    ownerDialog() {
      // This is incremented to force re-render of the owner dialog
      this.ownerDialogKey += 1;
    },
  },
  methods: {
    setVersion({ version }) {
      this.setRouteVersion(version);
    },
    setRouteVersion(newVersion) {
      const version = newVersion || draftVersion;

      if (this.$route.params.version !== version) {
        this.$router.replace({
          ...this.$route,
          params: {
            ...this.$route.params,
            version,
          },
        });
      }
    },
    formatDateTime(datetimeStr) {
      const datetime = moment(datetimeStr);
      const date = datetime.format('LL');
      const time = datetime.format('hh:mm A');

      return `${date} at ${time}`;
    },
    timelineVersionItemColor({ version }) {
      const { publishDandiset } = this;

      if (publishDandiset && version === publishDandiset.version) { return 'primary'; }
      if (!publishDandiset && version === draftVersion) {
        return 'amber darken-4';
      }

      return 'grey';
    },
  },
};
</script>
