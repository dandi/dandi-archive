<template>
  <v-card
    v-if="currentDandiset"
    height="100%"
    class="rounded-0 elevation-0"
  >
    <v-card-title>
      Dandiset Actions
    </v-card-title>

    <v-list
      class="px-4"
      density="compact"
    >
      <!-- Download -->
      <DownloadDialog />

      <!-- Cite As -->
      <div v-if="currentDandiset.dandiset.embargo_status === 'OPEN'">
        <CiteAsDialog />
      </div>

      <!-- Contact -->
      <ContactDialog />

      <!-- Open With -->
      <ExternalDandisetServicesDialog />
    </v-list>

    <v-list
      class="px-4"
      density="compact"
    >
      <!-- Files -->
      <v-list-item
        id="view-data"
        :disabled="unembargoInProgress"
        :to="fileBrowserLink"
        exact
        class="justify-space-between border border-b-0 rounded-t"
      >
        <template #prepend>
          <v-icon
            color="primary"
            start
          >
            mdi-folder
          </v-icon>
          <v-list-item-title>Files</v-list-item-title>
        </template>
      </v-list-item>

      <!-- Metadata -->
      <v-list-item
        id="view-edit-metadata"
        class="justify-space-between border rounded-b"
        @click="openMeditor = true"
      >
        <template #prepend>
          <v-icon
            color="primary"
            start
          >
            mdi-note-text
          </v-icon>
          <v-list-item-title>Metadata</v-list-item-title>
        </template>
      </v-list-item>
    </v-list>

    <v-list
      class="px-4"
      density="compact"
    >
      <!-- Manifest -->
      <v-list-item
        class="justify-space-between border rounded"
        :href="manifestLocation"
      >
        <template #prepend>
          <v-icon
            color="primary"
            start
          >
            mdi-clipboard
          </v-icon>
          <v-list-item-title>Manifest</v-list-item-title>
        </template>
      </v-list-item>
    </v-list>

    <!-- Share button -->
    <div class="mt-6 mb-4">
      <v-row
        no-gutters
        class="justify-center"
      >
        <v-btn
          variant="outlined"
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
