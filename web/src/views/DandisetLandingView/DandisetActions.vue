<template>
  <v-card
    v-if="currentDandiset"
    height="100%"
    class="rounded-0 elevation-0"
  >
    <v-card-title>
      Dandiset Actions
    </v-card-title>

    <v-list class="px-4">
      <DownloadDialog />
      <div v-if="currentDandiset.dandiset.embargo_status === 'OPEN'">
        <CiteAsDialog />
      </div>
      <ContactDialog />
      <ExternalDandisetServicesDialog />
    </v-list>

    <!-- Files and Metadata buttons
    <div>
      <v-row no-gutters>
        <v-btn
          id="view-data"
          variant="outlined"
          block
          :disabled="unembargoInProgress"
          :to="fileBrowserLink"
          exact
          class="justify-space-between"
        >
          <v-icon
            start
            color="primary"
          >
            mdi-folder
          </v-icon>
          <span>Files</span>
        </v-btn>
      </v-row>
      <v-btn
        id="view-edit-metadata"
        variant="outlined"
        block
        class="justify-space-between"
        @click="openMeditor = true"
      >
        <v-icon
          start
          color="primary"
        >
          mdi-note-text
        </v-icon>
        <span>Metadata</span>
      </v-btn>
    </div>

    <div class="my-4">
      <v-row no-gutters>
        <v-btn
          variant="outlined"
          block
          :href="manifestLocation"
          class="d-inline-flex justify-space-between align-center"
        >
          <v-icon
            start
            color="primary"
          >
            mdi-clipboard
          </v-icon>
          <span>Manifest</span>
        </v-btn>
      </v-row>
    </div>

    <!-- Share button
    <div class="mt-6 mb-4">
      <v-row
        no-gutters
        class="justify-center"
      >
        <v-btn
          variant="outlined"
          class="justify-center"
        >
          <ShareDialog text="Share" />
        </v-btn>
      </v-row>
    </div>-->
  </v-card>
</template>

<script setup lang="ts">
import type { ComputedRef } from 'vue';
import { computed } from 'vue';
import type { RouteLocationRaw } from 'vue-router';

import { dandiRest } from '@/rest';
import { useDandisetStore } from '@/stores/dandiset';

import { open as openMeditor } from '@/components/Meditor/state';
import DownloadDialog from './DownloadDialog.vue';
import CiteAsDialog from './CiteAsDialog.vue';
import ShareDialog from './ShareDialog.vue';
import ContactDialog from './ContactDialog.vue';
import ExternalDandisetServicesDialog from './ExternalDandisetServicesDialog.vue';

const store = useDandisetStore();

const currentDandiset = computed(() => store.dandiset);
const currentVersion = computed(() => store.version);
const unembargoInProgress = computed<boolean>(() => currentDandiset.value !== null && currentDandiset.value.dandiset.embargo_status === 'UNEMBARGOING')

const fileBrowserLink: ComputedRef<RouteLocationRaw|undefined> = computed(() => {
  if (!currentDandiset.value) {
    return undefined;
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
