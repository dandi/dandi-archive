<template>
  <v-container style="height: 100%;">
    <v-row v-if="selected">
      <v-col :cols="selected.length ? 8 : 12">
        <girder-file-manager
          ref="girderFileManager"
          selectable
          root-location-disabled
          :location.sync="location"
          :value="selected"
          :initial-items-per-page="25"
          :items-per-page-options="[10,25,50,100,-1]"
          @input="setSelected"
        >
          <template
            v-if="isDandiset"
            v-slot:headerwidget
          >
            <v-btn
              icon
              color="primary"
              :to="{ name: 'dandisetLanding', params: { id: location._id }}"
            >
              <v-icon>mdi-eye</v-icon>
            </v-btn>
          </template>
          <template
            v-slot:row-widget="{ item }"
          >
            <v-btn
              v-if="item._modelType === 'item'"
              icon
              small
              color="primary"
              :href="itemDownloadLink(item)"
            >
              <v-icon>mdi-download</v-icon>
            </v-btn>
          </template>
        </girder-file-manager>
      </v-col>
      <v-col
        v-if="selected.length"
        cols="4"
      >
        <girder-data-details
          :value="selected"
          :action-keys="actions"
          @action="handleAction"
        />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import {
  mapGetters,
  mapMutations,
  mapState,
  mapActions,
} from 'vuex';
import { DataDetails as GirderDataDetails } from '@girder/components/src/components';
import { DefaultActionKeys } from '@girder/components/src/components/DataDetails.vue';
import { FileManager as GirderFileManager } from '@girder/components/src/components/Snippet';

import {
  getLocationFromRoute,
} from '@/utils';

import girderRest from '@/rest';

// redirect to "Open JupyterLab"
const JUPYTER_ROOT = 'https://hub.dandiarchive.org';

const actionKeys = [
  {
    for: ['item'],
    name: 'Open JupyterLab',
    icon: 'mdi-language-python',
    color: 'primary',
    generateHref() {
      return JUPYTER_ROOT;
    },
    target: '_blank',
  },
  // Download for items only
  DefaultActionKeys[1],
];

export default {
  components: { GirderDataDetails, GirderFileManager },
  computed: {
    isDandiset() {
      return !!(this.location && this.location.meta && this.location.meta.dandiset);
    },
    actions() {
      const actions = [...actionKeys];
      const canDelete = (resource) => (
        (resource._modelType === 'folder' && resource._accessLevel === 2)
        || (resource._modelType === 'item' && this.location._accessLevel === 2)
      );

      if (
        this.selected.length === 1
        && this.selected[0].meta
        && this.selected[0].meta.dandiset
      ) {
        const id = this.selected[0]._id;

        actions.push({
          for: ['folder'],
          name: 'View DANDI Metadata',
          icon: 'mdi-pencil',
          color: 'primary',
          handler() {
            // eslint-disable-next-line
              this.$router.push({
              name: 'dandiset-metadata-viewer',
              params: { id },
            });
          },
        });
      }

      if (this.selected.every((item) => canDelete(item))) {
        actions.push(DefaultActionKeys[3]);
      }

      return actions;
    },
    location: {
      get() {
        return this.$store.state.girder.browseLocation;
      },
      set(value) {
        this.setBrowseLocation(value);
      },
    },
    ...mapState('girder', ['selected']),
    ...mapGetters('girder', ['loggedIn']),
  },
  watch: {
    location(newValue) {
      const { _modelType, _id } = this.$route.params;

      if (newValue._modelType !== _modelType || newValue._id !== _id) {
        this.$router.push({ name: 'file-browser', params: { _modelType: newValue._modelType, _id: newValue._id } });
      }
    },
  },
  created() {
    const location = getLocationFromRoute(this.$route);
    this.setBrowseLocation(location);
    this.fetchFullLocation(location);
  },
  methods: {
    itemDownloadLink(item) {
      return `${girderRest.apiRoot}/item/${item._id}/download`;
    },
    async handleAction(action) {
      if (action.name === 'Delete') {
        await this.$refs.girderFileManager.refresh();
        this.setSelected([]);
      }
    },
    ...mapMutations('girder', ['setBrowseLocation', 'setSelected']),
    ...mapActions('girder', ['fetchFullLocation']),
  },
};
</script>
<style>
.girder-file-browser .secondary .row .spacer {
  display: none;
}
</style>
