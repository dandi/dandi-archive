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
        <span class="text-subtitle-1">Use the DANDI CLI on the command line:</span>
        <div
          class="d-flex justify-center"
          style="font-family: monospace;"
        >
          <v-sheet
            color="black"
            width="60%"
            class="white--text pl-2 py-1 text-left"
          >
            <div>> {{ downloadCommand }}</div>
            <div>> cd {{ dandisetIdentifier }}</div>
            <div>> dandi organize &lt;source_folder&gt; -f dry</div>
            <div>> dandi organize &lt;source_folder&gt;</div>
            <div>> dandi upload</div>
          </v-sheet>
        </div>
      </div>
      <div>
        <span class="text-subtitle-1">Don't have DANDI CLI?</span>
        <div>
          <span class="text-body-2 grey--text text--darken-1">
            <span class="text-body-2 grey--text text--darken-1">
              Follow the installation instructions in the
              <a href="https://docs.dandiarchive.org/user-guide-sharing/uploading-data">
                DANDI Docs
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

if (dandisetIdentifier.value === undefined) {
  throw new Error('store.dandiset must be defined');
}

const downloadCommand = computed(() => {
  return `dandi download ${window.location.origin}/dandiset/${dandisetIdentifier.value}/draft`
});
</script>
