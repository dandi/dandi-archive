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
            :value="selected"
            @input="setSelected" />
      </v-col>
      <v-col cols="4" v-if="selected.length">
        <girder-data-details :value="selected" :action-keys="actions" />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { mapGetters, mapMutations, mapState } from 'vuex';
import { Authentication as GirderAuth, DataDetails as GirderDataDetails } from '@girder/components/src/components';
import { DefaultActionKeys } from '@girder/components/src/components/DataDetails.vue';
import { FileManager as GirderFileManager } from '@girder/components/src/components/Snippet';

const JUPYTER_ROOT = process.env.JUPYTER_ROOT || '/jupyter/some_notebook'; // TODO url
const actionKeys = [
  {
    for: ['item'],
    name: 'Open in Jupyter',
    icon: 'mdi-language-python',
    color: 'primary',
    handler() {
      const { value: items } = this;
      window.open(`${JUPYTER_ROOT}?item=${items[0]._id}`, '_blank');
    },
  },
  ...DefaultActionKeys,
];

export default {
  components: { GirderAuth, GirderDataDetails, GirderFileManager },
  computed: {
    actions: () => actionKeys,
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
  methods: mapMutations(['setBrowseLocation', 'setSelected']),
};
</script>
