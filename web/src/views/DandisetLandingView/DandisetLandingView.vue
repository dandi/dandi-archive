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
import { draftVersion, dandisetHasVersion } from '@/utils';
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
        return {
          name: this.publishDandiset.name,
          description: this.publishDandiset.description,
          ...this.publishDandiset.meta.dandiset,
        };
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
        await this.$store.dispatch('dandiset/initializeDandisets', { identifier, version });
        if (!this.publishDandiset) { this.navigateToDefaultDandiset(); }
      },
    },
    async version(version) {
      // On version change, fetch the new dandiset (not initial)

      const { identifier } = this;
      if (version === draftVersion) {
        this.$store.commit('dandiset/setPublishDandiset', null);
      } else {
        await this.$store.dispatch('dandiset/fetchPublishDandiset', { identifier, version });

        // If the above await call didn't result in publishDandiset being set, navigate to a default
        if (!this.publishDandiset) { this.navigateToDefaultDandiset(); }
      }
    },
  },
  methods: {
    navigateToDefaultDandiset() {
      // Set default version to most recent if this dandiset has versions
      // Otherwise set it to draft
      let version = draftVersion;
      const { dandisetVersions: versions } = this;

      if (versions && versions.length) {
        if (dandisetHasVersion(versions, this.version)) { return; }
        if (this.version !== draftVersion) {
          // The version isn't 'draft', and isn't one of the known versions,
          // thus it's not valid, so redirect to latest version
          version = versions[0].version;
        }
      }
      this.navigateToVersion(version);
    },
    navigateToVersion(version) {
      if (this.$route.params.version === version) return;

      const route = {
        ...this.$route,
        params: {
          ...this.$route.params,
          version,
        },
      };
      this.$router.replace(route);
    },
    navigateBack() {
      const route = this.$route.params.origin || { name: 'publicDandisets' };
      this.$router.push(route);
      this.$store.dispatch('dandiset/uninitializeDandisets');
    },
  },
};
</script>
