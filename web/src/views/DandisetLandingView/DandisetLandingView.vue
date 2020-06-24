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
import { mapState, mapGetters } from 'vuex';

import SCHEMA from '@/assets/schema/dandiset.json';
import NEW_SCHEMA from '@/assets/schema/dandiset_new.json';
import NWB_SCHEMA from '@/assets/schema/dandiset_metanwb.json';

import DandisetSearchField from '@/components/DandisetSearchField.vue';
import { draftVersion, isPublishedVersion } from '@/utils';
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
    identifier: {
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
      dandisetVersions: (state) => state.versions,
    }),
  },
  watch: {
    identifier: {
      immediate: true,
      async handler(identifier) {
        const { version } = this;
        this.$store.dispatch('dandiset/initializeDandisets', { identifier, version });
      },
    },
    dandisetVersions(versions) {
      // Set default version to most recent if this dandiset has versions
      // Otherwise set it to draft

      // Only do this if no version was specified
      if (isPublishedVersion(this.version)) { return; }

      let version = draftVersion;
      if (versions && versions.length) { version = versions[0].version; }
      const route = {
        ...this.$route,
        params: {
          ...this.$route.params,
          version,
        },
      };
      this.$router.replace(route);
    },
  },
  methods: {
    navigateBack() {
      const route = this.$route.params.origin || { name: 'publicDandisets' };
      this.$router.push(route);
      this.$store.dispatch('dandiset/uninitializeDandisets');
    },
  },
};
</script>
