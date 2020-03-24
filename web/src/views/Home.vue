<template>
  <v-container style="height: 100%;">
    <v-row>
      <v-col :cols="selected.length ? 8 : 12">
        <girder-file-manager
          :selectable="true"
          :location.sync="location"
          :upload-enabled="false"
          :value="selected"
          @input="setSelected"
          :initial-items-per-page="25"
          :items-per-page-options="[10,25,50,100,-1]"
        >
          <template v-slot:headerwidget v-if="isDandiset">
            <v-btn icon color="primary" :to="`/dandiset-meta/${location._id}`">
              <v-icon>mdi-eye</v-icon>
            </v-btn>
          </template>
        </girder-file-manager>
      </v-col>
      <v-col cols="4" v-if="selected.length">
        <girder-data-details :value="selected" :action-keys="actions" />
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
  getPathFromLocation,
  getLocationFromRoute,
  getSelectedFromRoute,
  getPathFromSelected,
} from '@/utils';

// redirect to "Open JupyterLab"
const JUPYTER_ROOT = 'https://hub.dandiarchive.org';

const actionKeys = [
  {
    for: ['item'],
    name: 'Open JupyterLab',
    icon: 'mdi-language-python',
    color: 'primary',
    handler() {
      window.open(`${JUPYTER_ROOT}`, '_blank');
    },
  },
  ...DefaultActionKeys.slice(1, 3),
];

export default {
  components: { GirderDataDetails, GirderFileManager },
  computed: {
    isDandiset() {
      return !!(this.location && this.location.meta && this.location.meta.dandiset);
    },
    actions() {
      let actions = actionKeys;
      console.log(actions);
      if (
        this.selected.length === 1
        && this.selected[0].meta
        && this.selected[0].meta.dandiset
      ) {
        const id = this.selected[0]._id;

        actions = [
          {
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
          },
          ...actionKeys,
        ];
      }

      return actions;
    },
    location: {
      get() {
        return this.browseLocation;
      },
      set(value) {
        this.setBrowseLocation(value);
      },
    },
    ...mapState(['browseLocation', 'selected']),
    ...mapGetters(['loggedIn']),
  },
  watch: {
    browseLocation(value) {
      const newPath = getPathFromLocation(value) + getPathFromSelected(this.selected);
      if (this.$route.path !== newPath) {
        this.$router.push(newPath);
      }
    },
    selected(selected) {
      const newPath = getPathFromLocation(this.location) + getPathFromSelected(selected);
      if (this.$route.path !== newPath) {
        this.$router.push(newPath);
      }
    },
    $route(to) {
      const location = getLocationFromRoute(to);
      const selected = getSelectedFromRoute(to);
      if (location._id !== this.location._id) {
        this.location = location;
      }
      if (
        selected.length !== this.selected.length
        || selected.find((model, i) => (
          model._id !== (this.selected[i] ? this.selected[i]._id : null)
        ))
      ) {
        // Same reason as what it says in store.js
        this.$nextTick(() => {
          this.setSelected(selected);
        });
      }
    },
  },
  created() {
    const location = getLocationFromRoute(this.$route);
    const selected = getSelectedFromRoute(this.$route);
    this.setBrowseLocation(location);
    this.fetchFullLocation(location);
    this.setSelected(selected);
  },
  methods: {
    ...mapMutations(['setBrowseLocation', 'setSelected']),
    ...mapActions(['fetchFullLocation']),
  },
};
</script>
<style>
.girder-file-browser .secondary .row .spacer {
  display: none;
}
</style>
