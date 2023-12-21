<template>
  <v-sheet
    v-if="dandisetIdentifier"
    class="d-flex"
    height="70vh"
  >
    <v-row
      class="d-flex flex-column justify-center text-center"
    >
      <div class="text-h6 font-weight-light">
        This Dandiset does not currently have any files associated with it,
        but this is where they will appear once they're added.
      </div>
      <div class="my-7">
        <span class="text-subtitle-1">For NWB datasets, use the DANDI CLI on the command line:</span>
        <div
          class="d-flex justify-center"
          style="font-family: monospace;"
        >
          <v-sheet
            color="black"
            width="60%"
            class="white--text pl-2 py-1 text-left"
          >
            <div>> dandi download https://dandiarchive.org/dandiset/{{ dandisetIdentifier }}/draft</div>
            <div>> cd {{ dandisetIdentifier }}</div>
            <div>> dandi organize &lt;source_folder&gt; -f dry</div>
            <div>> dandi organize &lt;source_folder&gt;</div>
            <div>> dandi upload</div>
          </v-sheet>
        </div>
        <span class="text-subtitle-1">
          (For BIDS datasets, use the DANDI CLI with similar instructions found in the 
          <a href="https://www.dandiarchive.org/handbook/13_upload/#data-uploadmanagement-workflow">
            DANDI handbook
          </a>.)
        </span>
      </div>
      <div>
        <span class="text-subtitle-1">Don't have DANDI CLI?</span>
        <div>
          <span class="text-body-2 grey--text text--darken-1">
            <span class="text-body-2 grey--text text--darken-1">
              Follow the installation instructions in the
              <a href="https://www.dandiarchive.org/handbook/10_using_dandi/#dandi-python-client">
                DANDI handbook
              </a> .
            </span>
          </span>
        </div>
      </div>
    </v-row>
  </v-sheet>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useDandisetStore } from '@/stores/dandiset';

const store = useDandisetStore();
const dandisetIdentifier = computed(() => store.dandiset?.dandiset.identifier);
</script>
