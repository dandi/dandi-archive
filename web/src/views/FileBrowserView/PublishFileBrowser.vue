<template>
  <v-container>
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
              :to="{ name: 'dandisetLanding', params: { identifier: location.meta.dandiset.identifier }}"
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
import { FileManager as GirderFileManager } from '@girder/components/src/components/Snippet';

import {
  getLocationFromRoute,
} from '@/utils';


export default {
  name: 'PublishFileBrowser',
  components: { GirderFileManager },
  computed: {
    isDandiset() {
      return !!(this.location && this.location.meta && this.location.meta.dandiset);
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
