<template>
  <v-dialog
    v-if="meta && meta.name"
    v-model="dialog"
    offset-y
    min-width="420"
    max-width="500"
  >
    <template #activator="{ on }">
      <div
        class="d-inline"
        v-on="on"
      >
        <v-icon
          color="primary"
          style="cursor: pointer;"
        >
          mdi-share-variant
        </v-icon>
        {{ text }}
      </div>
    </template>

    <v-card>
      <v-toolbar
        flat
      >
        <v-toolbar-title>
          <span> Share "{{ meta.name }}"</span>
        </v-toolbar-title>
        <v-spacer />
        <v-btn
          icon
          x-smal
          @click="dialog = false"
        >
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-toolbar>
      <v-card-text>
        <span class="font-weight-black">
          Dandiset link:
        </span>
        <CopyText
          class="pa-2"
          :text="permalink"
          icon-hover-text="Copy Dandiset link to clipboard"
        />
      </v-card-text>
      <v-card-text
        v-if="doiLink"
      >
        <span class="font-weight-black">
          DOI link:
        </span>
        <CopyText
          class="pa-2"
          :text="doiLink"
          icon-hover-text="Copy DOI link to clipboard"
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
              style="text-decoration: none;"
              :url="permalink"
              :title="meta.name"
              :twitter-user="twitterUser"
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
import { defineComponent, computed, ref } from 'vue';

import CopyText from '@/components/CopyText.vue';
import { useDandisetStore } from '@/stores/dandiset';
import { dandiUrl } from '@/utils/constants';

// Twitter user to mention
const twitterUser = 'DANDIarchive';

export default defineComponent({
  name: 'ShareDialog',
  components: { CopyText },
  props: {
    text: {
      type: String,
      default: '',
    },
  },
  setup() {
    const store = useDandisetStore();

    const currentDandiset = computed(() => store.dandiset);
    const currentVersion = computed(() => store.version);
    const meta = computed(() => currentDandiset.value?.metadata);
    const permalink = computed(() => {
      if (currentDandiset.value?.dandiset && currentVersion.value) {
        return `${dandiUrl}/dandiset/${currentDandiset.value?.dandiset.identifier}/${currentVersion.value}`;
      }
      return '';
    });
    const doiLink = computed(() => (meta.value?.doi ? `https://doi.org/:${meta.value?.doi}` : ''));

    const dialog = ref(false);

    return {
      dialog, twitterUser, meta, permalink, doiLink,
    };
  },
});

</script>
