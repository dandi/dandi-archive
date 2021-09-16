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

    <!-- Download, Shareable Link, and Cite As buttons -->
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
              Download
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
              Cite As
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
          :to="fileBrowserLink"
        >
          <v-icon
            left
            color="primary"
          >
            mdi-folder
          </v-icon>
          Files
          <v-spacer />
        </v-btn>
      </v-row>
      <v-row no-gutters>
        <v-btn
          id="view-edit-metadata"
          outlined
          style="width: 100%"
          @click="$emit('edit')"
        >
          <v-icon
            left
            color="primary"
          >
            mdi-note-text
          </v-icon>
          Metadata
          <v-spacer />
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

export default defineComponent({
  name: 'DandisetActions',
  components: {
    CiteAsDialog,
    DownloadDialog,
  },
  setup() {
    const currentDandiset = computed(() => store.state.dandiset.publishDandiset);
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

    return {
      currentDandiset,
      currentVersion,
      fileBrowserLink,
    };
  },
});
</script>
