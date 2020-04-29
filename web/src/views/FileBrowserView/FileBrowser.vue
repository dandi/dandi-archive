<template>
  <v-container style="height: 100%;">
    <v-row v-if="selected">
      <v-col :cols="selected.length ? 8 : 12">
        <girder-file-manager
          :selectable="true"
          :location.sync="location"
          :upload-enabled="false"
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
        </girder-file-manager>
      </v-col>
      <v-col
        v-if="selected.length"
        cols="4"
      >
        <girder-data-details
          :value="selected"
          :action-keys="actions"
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
      let actions = actionKeys;
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
    location(newValue, oldValue) {
      if (
        !oldValue === null
        || newValue._modelType !== oldValue._modelType
        || newValue._id !== oldValue._id
      ) {
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
