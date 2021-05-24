<template>
  <div>
    <v-row class="mx-2 my-2">
      <h1 class="font-weight-regular">
        {{ meta.name }}
      </h1>
    </v-row>
    <v-card class="pb-2">
      <v-row
        class="mx-2"
        align="center"
      >
        <v-col>
          Get shareable link
          <v-menu
            offset-y
            left
            :close-on-content-click="false"
            min-width="500"
            max-width="500"
          >
            <template #activator="{ on }">
              <v-icon
                color="primary"
                v-on="on"
              >
                mdi-link
              </v-icon>
            </template>
            <v-card>
              <CopyText
                class="mx-2"
                :text="permalink"
                icon-hover-text="Copy permalink to clipboard"
              />
            </v-card>
          </v-menu>
        </v-col>
        <DownloadDialog>
          <template #activator="{ on }">
            <v-btn
              id="download"
              text
              v-on="on"
            >
              <v-icon
                color="primary"
                class="mr-2"
              >
                mdi-download
              </v-icon>
              Download
              <v-icon>mdi-menu-down</v-icon>
            </v-btn>
          </template>
        </DownloadDialog>
        <v-btn
          id="view-data"
          :to="fileBrowserLink"
          text
        >
          <v-icon
            color="primary"
            class="mr-2"
          >
            mdi-file-tree
          </v-icon>
          View Data
        </v-btn>
        <v-btn
          id="view-edit-metadata"
          text
          @click="$emit('edit')"
        >
          <v-icon
            color="primary"
            class="mr-2"
          >
            {{ metadataButtonIcon }}
          </v-icon>
          {{ metadataButtonText }}
        </v-btn>
        <template v-if="!DJANGO_API || publishDandiset.version == 'draft'">
          <v-tooltip
            left
            :disabled="publishDisabledMessage === null"
          >
            <template #activator="{ on }">
              <div v-on="on">
                <!-- TODO for now only admins can publish -->
                <v-btn
                  v-if="DJANGO_API"
                  id="publish"
                  text
                  :disabled="publishDisabledMessage !== null || !user || !user.admin"
                  @click="publish"
                >
                  <v-icon
                    color="success"
                    class="mr-2"
                  >
                    mdi-publish
                  </v-icon>
                  Publish
                </v-btn>
              </div>
            </template>
            {{ publishDisabledMessage }}
          </v-tooltip>
        </template>
      </v-row>

      <v-divider />

      <v-row :class="titleClasses">
        <v-card-title class="font-weight-regular">
          Description
        </v-card-title>
      </v-row>
      <v-row class="mx-1 mb-4 px-4 font-weight-light">
        {{ meta.description }}
      </v-row>

      <template v-for="key in Object.keys(extraFields).sort()">
        <template v-if="renderData(extraFields[key], schema.properties[key])">
          <v-divider :key="`${key}-divider`" />
          <v-row
            :key="`${key}-title`"
            :class="titleClasses"
          >
            <v-card-title class="font-weight-regular">
              {{ schema.properties[key].title || key }}
            </v-card-title>
          </v-row>
          <v-row
            :key="key"
            class="mx-2 mb-4"
          >
            <v-col class="py-0">
              <ListingComponent
                :field="key"
                :schema="schema.properties[key]"
                :data="extraFields[key]"
              />
            </v-col>
          </v-row>
        </template>
      </template>
    </v-card>
  </div>
</template>

<script>
import { mapState, mapGetters } from 'vuex';

import { dandiUrl } from '@/utils/constants';
import {
  girderRest, loggedIn, publishRest, user,
} from '@/rest';
import toggles from '@/featureToggle';

import CopyText from '@/components/CopyText.vue';
import DownloadDialog from './DownloadDialog.vue';
import ListingComponent from './ListingComponent.vue';

export default {
  name: 'DandisetMain',
  components: {
    CopyText,
    DownloadDialog,
    ListingComponent,
  },
  props: {
    schema: {
      type: Object,
      required: true,
    },
    meta: {
      type: Object,
      required: true,
    },
    userCanModifyDandiset: {
      type: Boolean,
      required: true,
    },
  },
  data() {
    return {
      titleClasses: 'mx-1',
      mainFields: [
        'name',
        'description',
        'identifier',
      ],
    };
  },
  computed: {
    loggedIn,
    user,
    publishDisabledMessage() {
      if (!this.loggedIn) {
        return 'You must be logged in to edit.';
      }

      if (!this.userCanModifyDandiset) {
        return 'You do not have permission to edit this dandiset.';
      }
      if (this.publishDandiset.status === 'Invalid') {
        return this.publishDandiset.validationError;
      }
      if (this.publishDandiset.status === 'Pending') {
        return 'This dandiset has not yet been validated.';
      }
      if (this.publishDandiset.status === 'Validating') {
        return 'Currently validating this dandiset.';
      }

      return null;
    },
    metadataButtonText() {
      return this.userCanModifyDandiset ? 'Edit metadata' : 'View metadata';
    },
    metadataButtonIcon() {
      return this.userCanModifyDandiset ? 'mdi-pencil' : 'mdi-eye';
    },
    fileBrowserLink() {
      if (toggles.DJANGO_API) {
        const { version } = this;
        const { identifier } = this.publishDandiset.meta.dandiset;
        // TODO: this probably does not work correctly yet
        return {
          name: 'fileBrowser',
          params: { identifier, version },
          query: {
            location: '',
          },
        };
      }
      const { version } = this;
      const { identifier } = this.girderDandiset.meta.dandiset;

      return { name: 'fileBrowser', params: { identifier, version } };
    },
    permalink() {
      return `${dandiUrl}/dandiset/${this.meta.identifier}/${this.version}`;
    },
    extraFields() {
      const { meta, mainFields } = this;
      const extra = Object.keys(meta).filter(
        (x) => !mainFields.includes(x) && x in this.schema.properties,
      );
      return extra.reduce((obj, key) => ({ ...obj, [key]: meta[key] }), {});
    },
    ...mapState('dandiset', {
      girderDandiset: (state) => state.girderDandiset,
      publishDandiset: (state) => state.publishDandiset,
    }),
    ...mapGetters('dandiset', ['version']),
  },
  asyncComputed: {
    lockOwner: {
      async get() {
        if (toggles.DJANGO_API) {
          return null;
        }
        const { data: owner } = await girderRest.get(`/dandi/${this.girderDandiset.meta.dandiset.identifier}/lock/owner`);
        if (!owner) {
          return null;
        }
        return owner;
      },
      // default to the publish lock message until the actual lock owner can be fetched
      default: { email: 'publish@dandiarchive.org' },
    },
  },
  methods: {
    async publish() {
      // TODO ungirderize
      const version = await publishRest.publish(this.publishDandiset.meta.dandiset.identifier);
      // re-initialize the dataset to load the newly published version
      await this.$store.dispatch('dandiset/initializeDandisets', { identifier: version.dandiset.identifier, version: version.version });
    },
    renderData(data, schema) {
      if (data === null) { return false; }
      if (schema.type === 'array' && Array.isArray(data) && data.length === 0) {
        return false;
      }

      return true;
    },
  },
};
</script>
