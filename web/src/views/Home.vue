<template>
  <v-row>
    <v-col v-if="!loggedIn" lg=4 md=5 sm=12>
      <girder-auth
          :force-otp="false"
          :show-forgot-password="false"
          :oauth="true"
      />
    </v-col>
    <v-col>
      <girder-file-manager
          :selectable="true"
          :location.sync="location"
          :upload-enabled="false"
          @selection-changed="selectionChanged" />
    </v-col>
  </v-row>
</template>

<script>
import {
  mapActions, mapGetters, mapMutations, mapState,
} from 'vuex';
import { Authentication as GirderAuth } from '@girder/components/src/components';
import { FileManager as GirderFileManager } from '@girder/components/src/components/Snippet';

export default {
  components: { GirderAuth, GirderFileManager },
  computed: {
    location: {
      get() {
        return this.browseLocation;
      },
      set(value) {
        this.setBrowseLocation(value);
      },
    },
    ...mapState(['browseLocation']),
    ...mapGetters(['loggedIn']),
  },
  methods: {
    selectionChanged(event) {
      this.setSelected(event);
    },
    ...mapActions(['setSelected']),
    ...mapMutations(['setBrowseLocation']),
  },
};
</script>
