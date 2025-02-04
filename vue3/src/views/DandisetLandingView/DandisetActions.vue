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
        <DownloadDialog />
      </v-row>
      <v-row
        v-if="currentDandiset.dandiset.embargo_status === 'OPEN'"
        no-gutters
      >
        <CiteAsDialog>
          <template
            #activator="{ on }"
          >
            <v-btn
              id="cite_as"
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
      <v-row
        no-gutters
      >
        <ContactDialog />
      </v-row>
      <v-row
        no-gutters
      >
        <ExternalDandisetServicesDialog />
      </v-row>
    </div>

    <!-- Files and Metadata buttons -->
    <div>
      <v-row no-gutters>
        <v-btn
          id="view-data"
          outlined
          block
          :disabled="unembargo_in_progress"
          :to="fileBrowserLink"
          exact
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
      <v-btn
        id="view-edit-metadata"
        outlined
        block
      >
        <!-- TODO: put this back in the v-btn when we have the meditor working -->
        <!-- @click="openMeditor = true" -->
        <v-icon
          left
          color="primary"
        >
          mdi-note-text
        </v-icon>
        <span>Metadata</span>
        <v-spacer />
      </v-btn>
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

<script setup lang="ts">
import type { ComputedRef } from 'vue';
import { computed } from 'vue';
import type { Location } from 'vue-router';

import { dandiRest } from '@/rest';
import { useDandisetStore } from '@/stores/dandiset';

// import { open as openMeditor } from '@/components/Meditor/state';
import DownloadDialog from './DownloadDialog.vue';
import CiteAsDialog from './CiteAsDialog.vue';
import ShareDialog from './ShareDialog.vue';
import ContactDialog from './ContactDialog.vue';
import ExternalDandisetServicesDialog from './ExternalDandisetServicesDialog.vue';

const store = useDandisetStore();

const currentDandiset = computed(() => store.dandiset);
const currentVersion = computed(() => store.version);
const unembargo_in_progress = computed(() => currentDandiset.value && currentDandiset.value.dandiset.embargo_status === 'UNEMBARGOING')

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

const manifestLocation = computed(
  () => dandiRest.assetManifestURI(
    currentDandiset.value?.dandiset.identifier || '',
    currentDandiset.value?.version || '',
  ),
);

</script>

<style scoped>
.v-btn--outlined {
  border: thin solid #E0E0E0;
  color: #424242;
  font-weight: 400;
}
</style>