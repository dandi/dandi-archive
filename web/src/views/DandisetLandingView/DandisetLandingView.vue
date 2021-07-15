<template>
  <div
    v-if="schema"
    v-page-title="meta.name"
  >
    <template v-if="edit && Object.entries(meta).length">
      <meditor
        :schema="schema"
        :model="meta"
        :readonly="!userCanModifyDandiset"
        @close="edit = false"
      />
    </template>
    <template v-else>
      <v-toolbar class="grey darken-2 white--text">
        <v-row>
          <v-col cols="12">
            <DandisetSearchField />
          </v-col>
        </v-row>
      </v-toolbar>
      <v-container
        v-if="currentDandiset"
        fluid
        class="grey lighten-4"
      >
        <v-progress-linear
          v-if="!currentDandiset || loading"
          indeterminate
        />
        <v-row>
          <v-col>
            <DandisetMain
              :schema="schema"
              :meta="meta"
              :user-can-modify-dandiset="userCanModifyDandiset"
              @edit="edit = true"
            />
          </v-col>
          <v-col
            v-if="!$vuetify.breakpoint.smAndDown"
            cols="3"
          >
            <DandisetDetails />
          </v-col>
        </v-row>
        <v-row v-if="$vuetify.breakpoint.smAndDown">
          <v-col
            cols="12"
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
import { publishRest, user } from '@/rest';
import Meditor from './Meditor.vue';
import DandisetMain from './DandisetMain.vue';
import DandisetDetails from './DandisetDetails.vue';

export default {
  name: 'DandisetLandingView',
  components: {
    Meditor,
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
      readonly: false,
    };
  },
  computed: {
    currentDandiset() {
      return this.publishDandiset;
    },
    meta() {
      if (this.publishDandiset) {
        return this.publishDandiset.metadata;
      }

      return {};
    },
    ...mapState('dandiset', {
      publishDandiset: (state) => state.publishDandiset,
      loading: (state) => state.loading,
      dandisetVersions: (state) => state.versions,
      schema: (state) => state.schema,
    }),
    user,
  },
  asyncComputed: {
    userCanModifyDandiset: {
      async get() {
        // published versions are never editable
        if (this.publishDandiset.metadata.version !== 'draft') {
          return false;
        }

        if (!this.user) {
          return false;
        }

        if (this.user.admin) {
          return true;
        }

        const { identifier } = this.publishDandiset.dandiset;
        const { data: owners } = await publishRest.owners(identifier);
        const userExists = owners.find((owner) => owner.username === this.user.username);
        return !!userExists;
      },
      default: false,
    },
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
      const { identifier } = this;
      await this.$store.dispatch('dandiset/fetchPublishDandiset', { identifier, version });
      // If the above await call didn't result in publishDandiset being set, navigate to a default
      if (!this.publishDandiset) {
        // Omitting version will fetch the most recent version instead
        await this.$store.dispatch('dandiset/fetchPublishDandiset', { identifier });
        this.navigateToVersion(this.publishDandiset.version);
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
  },
};
</script>
