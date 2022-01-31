<template>
  <v-card
    v-if="currentDandiset"
    height="100%"
    class="px-3 py-1 mb-3"
    outlined
  >
    <div class="black--text text-h5 mt-2">
      Dandiset Actions
    </div>

    <!-- Download and Cite As buttons -->
    <div class="my-4">
      <v-row no-gutters>
        <DownloadDialog>
          <template
            #activator="{ on }"
            class="justify-left"
          >
            <v-btn
              id="download"
              outlined
              block
              v-on="on"
            >
              <v-icon
                color="primary"
                left
              >
                mdi-download
              </v-icon>
              <span>Download</span>
              <v-spacer />
              <v-icon right>
                mdi-chevron-down
              </v-icon>
            </v-btn>
          </template>
        </DownloadDialog>
      </v-row>
      <v-row no-gutters>
        <CiteAsDialog>
          <template
            #activator="{ on }"
            class="justify-left"
          >
            <v-btn
              id="download"
              outlined
              block
              v-on="on"
            >
              <v-icon
                color="primary"
                left
              >
                mdi-format-quote-close
              </v-icon>
              <span>Cite As</span>
              <v-spacer />
              <v-icon right>
                mdi-chevron-down
              </v-icon>
            </v-btn>
          </template>
        </CiteAsDialog>
      </v-row>
    </div>

    <!-- Files and Metadata buttons -->
    <div>
      <v-row no-gutters>
        <v-btn
          id="view-data"
          outlined
          block
          :disabled="currentDandiset.dandiset.embargo_status === 'UNEMBARGOING'"
          :to="fileBrowserLink"
        >
          <v-icon
            left
            color="primary"
          >
            mdi-folder
          </v-icon>
          <span>Files</span>
          <v-spacer />
        </v-btn>
      </v-row>
      <v-row no-gutters>
        <v-btn
          id="view-edit-metadata"
          outlined
          block
          :to="meditorLink"
        >
          <v-icon
            left
            color="primary"
          >
            mdi-note-text
          </v-icon>
          <span>Metadata</span>
          <v-spacer />
        </v-btn>
      </v-row>
    </div>

    <div class="my-4">
      <v-row no-gutters>
        <v-btn
          outlined
          block
          :href="manifestLocation"
        >
          <v-icon
            left
            color="primary"
          >
            mdi-clipboard
          </v-icon>
          <span>Manifest</span>
          <v-spacer />
        </v-btn>
      </v-row>
    </div>

    <!-- Share button -->
    <div class="mt-6 mb-4">
      <v-row
        no-gutters
        class="justify-center"
      >
        <v-btn
          outlined
          class="justify-center"
        >
          <ShareDialog text="Share" />
        </v-btn>
      </v-row>
    </div>
  </v-card>
</template>

<script lang="ts">
import { defineComponent, computed, ComputedRef } from '@vue/composition-api';
import { Location } from 'vue-router';

import store from '@/store';

import DownloadDialog from './DownloadDialog.vue';
import CiteAsDialog from './CiteAsDialog.vue';
import ShareDialog from './ShareDialog.vue';

export default defineComponent({
  name: 'DandisetActions',
  components: {
    CiteAsDialog,
    DownloadDialog,
    ShareDialog,
  },
  setup() {
    const currentDandiset = computed(() => store.state.dandiset.dandiset);
    const currentVersion = computed(() => store.getters.dandiset.version);

    const fileBrowserLink: ComputedRef<Location|null> = computed(() => {
      if (!currentDandiset.value) {
        return null;
      }
      const version: string = currentVersion.value;
      const { identifier } = currentDandiset.value.dandiset;
      return {
        name: 'fileBrowser',
        params: { identifier, version },
        query: {
          location: '',
        },
      };
    });

    const meditorLink: ComputedRef<Location|null> = computed(() => {
      if (!currentDandiset.value) {
        return null;
      }
      const version: string = currentVersion.value;
      const { identifier } = currentDandiset.value.dandiset;
      return {
        name: 'metadata',
        params: { identifier, version },
      };
    });

    const manifestLocation = computed(
      () => currentDandiset.value?.metadata?.manifestLocation[0],
    );

    return {
      currentDandiset,
      currentVersion,
      fileBrowserLink,
      meditorLink,
      manifestLocation,
    };
  },
});
</script>

<style scoped>
.v-btn--outlined {
  border: thin solid #E0E0E0;
  color: #424242;
  font-weight: 400;
}
</style>
