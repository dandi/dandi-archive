<template>
  <div
    v-if="schema"
    v-page-title="meta.name"
  >
    <template v-if="edit && Object.entries(meta).length">
      <meditor
        v-if="toggles.DJANGO_API"
        :schema="schema"
        :model="meta"
        @close="edit = false"
      />
      <meta-editor
        v-else
        :schema="schema"
        :model="meta"
        @close="edit = false"
      />
    </template>
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
          v-if="!currentDandiset || loading"
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
        v-if="currentDandiset"
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

import DandisetSearchField from '@/components/DandisetSearchField.vue';
import { draftVersion } from '@/utils/constants';
import toggles from '@/featureToggle';
import MetaEditor from './MetaEditor.vue';
import Meditor from './Meditor.vue';
import DandisetMain from './DandisetMain.vue';
import DandisetDetails from './DandisetDetails.vue';

export default {
  name: 'DandisetLandingView',
  components: {
    Meditor,
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
  },
  data() {
    return {
      edit: false,
      detailsPanel: true,
      toggles,
    };
  },
  computed: {
    currentDandiset() {
      if (toggles.DJANGO_API) {
        return this.publishDandiset;
      }
      return this.girderDandiset;
    },
    meta() {
      if (this.publishDandiset) {
        return {
          name: this.publishDandiset.name,
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
      schema: (state) => state.schema,
    }),
  },
  watch: {
    identifier: {
      immediate: true,
      async handler(identifier) {
        const { version } = this;
        await this.$store.dispatch('dandiset/initializeDandisets', { identifier, version });
        // TODO: check for invalid versions here
      },
    },
    async version(version) {
      // On version change, fetch the new dandiset (not initial)
      if (toggles.DJANGO_API) {
        const { identifier } = this;
        await this.$store.dispatch('dandiset/fetchPublishDandiset', { identifier, version });
        // If the above await call didn't result in publishDandiset being set, navigate to a default
        if (!this.publishDandiset) {
          // Omitting version will fetch the most recent version instead
          await this.$store.dispatch('dandiset/fetchPublishDandiset', { identifier });
          this.navigateToVersion(this.publishDandiset.version);
        }
      } else {
        // With girder there is only two permissible versions, null and 'draft'
        // eslint-disable-next-line no-lonely-if
        if (version) {
          this.navigateToVersion(draftVersion);
        } else {
          this.navigateToVersion(version);
        }
      }
    },
  },
  methods: {
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
