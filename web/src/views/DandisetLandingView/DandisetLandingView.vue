<template>
  <div v-page-title="meta.name">
    <meta-editor
      v-if="edit && Object.entries(meta).length"
      :schema="schema"
      :model="meta"
      :create="create"
      @close="edit = false"
    />
    <template v-else>
      <v-toolbar class="grey darken-2 white--text">
        <v-btn
          icon
          @click="navigateBack"
        >
          <v-icon color="white">
            mdi-arrow-left
          </v-icon>
        </v-btn>
        <v-toolbar-title>
          Dandiset Dashboard
        </v-toolbar-title>
        <v-progress-circular
          v-if="!girderDandiset || loading"
          indeterminate
          class="ml-3"
        />
        <v-spacer />
        <DandisetSearchField />
        <v-btn
          icon
          @click="detailsPanel = !detailsPanel"
        >
          <v-icon color="white">
            <template v-if="detailsPanel">
              mdi-chevron-up
            </template>
            <template v-else>
              mdi-chevron-down
            </template>
          </v-icon>
        </v-btn>
      </v-toolbar>
      <v-container
        v-if="girderDandiset"
        fluid
        class="grey lighten-4"
      >
        <v-row v-if="$vuetify.breakpoint.smAndDown">
          <v-col
            v-if="detailsPanel"
            cols="12"
          >
            <DandisetDetails />
          </v-col>
        </v-row>
        <v-row>
          <v-col>
            <DandisetMain
              :schema="schema"
              :meta="meta"
              @edit="edit = true"
            />
          </v-col>
          <v-col
            v-if="detailsPanel && !$vuetify.breakpoint.smAndDown"
            cols="3"
          >
            <DandisetDetails />
          </v-col>
        </v-row>
      </v-container>
    </template>
  </div>
</template>

<script>
import { mapState } from 'vuex';

import SCHEMA from '@/assets/schema/dandiset.json';
import NEW_SCHEMA from '@/assets/schema/dandiset_new.json';
import NWB_SCHEMA from '@/assets/schema/dandiset_metanwb.json';

import DandisetSearchField from '@/components/DandisetSearchField.vue';
import { isPublishedVersion } from '@/utils';
import MetaEditor from './MetaEditor.vue';
import DandisetMain from './DandisetMain.vue';
import DandisetDetails from './DandisetDetails.vue';


export default {
  name: 'DandisetLandingView',
  components: {
    MetaEditor,
    DandisetMain,
    DandisetSearchField,
    DandisetDetails,
  },
  props: {
    id: {
      type: String,
      required: true,
    },
    version: {
      type: String,
      required: false,
      default: null,
    },
    create: {
      type: Boolean,
      required: false,
      default: () => false,
    },
  },
  data() {
    return {
      edit: false,
      detailsPanel: true,
    };
  },
  computed: {
    schema() {
      if (this.create) {
        return NEW_SCHEMA;
      }

      if (this.edit) {
        return SCHEMA;
      }

      const properties = { ...SCHEMA.properties, ...NWB_SCHEMA.properties };
      const required = [...SCHEMA.required, ...NWB_SCHEMA.required];

      return { properties, required };
    },
    meta() {
      if (this.publishDandiset) {
        return { ...this.publishDandiset.meta.dandiset };
      }

      if (
        !this.girderDandiset
        || !this.girderDandiset.meta
        || !this.girderDandiset.meta.dandiset
      ) {
        return {};
      }

      return { ...this.girderDandiset.meta.dandiset };
    },
    ...mapState('dandiset', {
      girderDandiset: (state) => state.girderDandiset,
      publishDandiset: (state) => state.publishDandiset,
      loading: (state) => state.loading,
    }),
  },
  watch: {
    id: {
      immediate: true,
      async handler(value) {
        // If we ever change the URL to contain the dandiset ID instead of the
        // girder folder ID, this should be moved into the store

        if (!this.girderDandiset || !this.meta.length) {
          this.$store.dispatch('dandiset/fetchGirderDandiset', { girderId: value });
        }
      },
    },
    girderDandiset: {
      immediate: true,
      async handler(value) {
        const { version } = this;
        if (value && isPublishedVersion(version)) {
          const { _id: girderId, meta: { dandiset: { identifier } } } = value;
          this.$store.dispatch('dandiset/fetchPublishDandiset', { identifier, girderId, version });
        }
      },
    },
  },
  methods: {
    navigateBack() {
      const route = this.$route.params.origin || { name: 'publicDandisets' };
      this.$router.push(route);
    },
  },
};
</script>
