<template>
  <v-container>
    <v-row v-if="!loggedIn">
      <v-col cols="12">
        <girder-auth :force-otp="false"  :show-forgot-password="false"  :oauth="true" />
      </v-col>
    </v-row>
    <v-row>
      <v-col :cols="selected.length ? 8 : 12">
        <girder-file-manager
            :selectable="true"
            :location.sync="location"
            :upload-enabled="false"
            @selection-changed="setSelected" />
      </v-col>
      <v-col cols="4" v-if="selected.length">
        <girder-data-details :value="selected"/>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { mapGetters, mapMutations, mapState } from 'vuex';
import { Authentication as GirderAuth, DataDetails as GirderDataDetails } from '@girder/components/src/components';
import { FileManager as GirderFileManager } from '@girder/components/src/components/Snippet';

export default {
  components: { GirderAuth, GirderDataDetails, GirderFileManager },
  computed: {
    location: {
      get() {
        return this.browseLocation;
      },
      set(value) {
        this.setBrowseLocation(value);
      },
    },
    // TODO selected should actually be passed down into the data browser, see
    // https://github.com/girder/girder_web_components/pull/181
    ...mapState(['browseLocation', 'selected']),
    ...mapGetters(['loggedIn']),
  },
  methods: mapMutations(['setBrowseLocation', 'setSelected']),
};
</script>
