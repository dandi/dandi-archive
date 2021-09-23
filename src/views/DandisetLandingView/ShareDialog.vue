<template>
  <v-dialog
    v-model="dialog"
    offset-y
    min-width="420"
    max-width="500"
  >
    <template #activator="{ on }">
      <div v-on="on">
        <v-icon
          color="primary"
        >
          mdi-share-variant
        </v-icon>
        {{ text }}
      </div>
    </template>

    <v-card>
      <v-card-title>
        <v-btn
          icon
          x-small
          :right="true"
          :absolute="true"
          @click="dialog = false"
        >
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>
      <v-card-title class="text-h6">
        {{ meta.name }}
      </v-card-title>
      <v-card-text>
        <div>
          <span
            v-for="author in meta.contributor"
            :key="author.name + author.identifier"
            class="text-body-1"
          >
            {{ author.name }}
          </span>
        </div>
      </v-card-text>
      <v-card-text>
        <span class="font-weight-black">
          Share this article:
        </span>
        <CopyText
          class="pa-2"
          :text="permalink"
          icon-hover-text="Copy permalink to clipboard"
        />
      </v-card-text>
      <v-divider class="mx-4" />
      <v-card-actions>
        <v-list-item class="grow">
          <v-row
            align="center"
          >
            <ShareNetwork
              network="twitter"
              :url="permalink"
              :title="meta.name"
              :hashtags="hashtags"
            >
              <v-icon
                class="mr-1"
                color="blue"
                large
              >
                mdi-twitter
              </v-icon>
            </ShareNetwork>
          </v-row>
        </v-list-item>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
import { defineComponent, computed, ref } from '@vue/composition-api';

import store from '@/store';
import { dandiUrl } from '@/utils/constants';

// comma-delimited string of hashtags to be used in twitter share
const hashtags = 'dandi';

export default defineComponent({
  name: 'ShareDialog',
  props: {
    text: {
      type: String,
      default: '',
    },
  },
  setup() {
    const currentDandiset = computed(() => store.state.dandiset.publishDandiset);
    const currentVersion = computed(() => store.getters.dandiset.version);
    const meta = computed(() => currentDandiset.value?.metadata);
    const permalink = computed(() => {
      if (currentDandiset.value?.dandiset && currentVersion.value) {
        return `${dandiUrl}/dandiset/${currentDandiset.value?.dandiset.identifier}/${currentVersion.value}`;
      }
      return '';
    });

    const dialog = ref(false);

    return {
      dialog, hashtags, meta, permalink,
    };
  },
});

</script>
