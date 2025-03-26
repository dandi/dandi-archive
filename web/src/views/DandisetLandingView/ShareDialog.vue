<template>
  <v-dialog
    v-if="meta && meta.name"
    v-model="dialog"
    :min-width="420"
    :max-width="500"
  >
    <template #activator="{ props }">
      <div
        class="d-inline"
        v-bind="props"
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
          Share "{{ meta.name }}"
        </v-toolbar-title>
        <v-spacer />
        <v-btn
          icon="mdi-close"
          size="small"
          @click="dialog = false"
        />
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
          <ShareNetwork
            v-slot="{ share }"
            network="twitter"
            style="text-decoration: none;"
            :url="permalink"
            :title="meta.name"
            :twitter-user="twitterUser"
          >
            <v-btn
              icon
              @click="share"
            >
              <v-icon
                class="mr-1"
                color="blue"
                size="large"
              >
                mdi-twitter
              </v-icon>
            </v-btn>
          </ShareNetwork>
        </v-list-item>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import CopyText from '@/components/CopyText.vue';
import { useDandisetStore } from '@/stores/dandiset';
import { computed, ref } from 'vue';
import { ShareNetwork } from "vue3-social-sharing";


defineProps({
  text: {
    type: String,
    default: '',
  },
});

// // Twitter user to mention
const twitterUser = 'DANDIarchive';

const store = useDandisetStore();
const dialog = ref(false);

const currentDandiset = computed(() => store.dandiset);
const currentVersion = computed(() => store.version);
const meta = computed(() => currentDandiset.value?.metadata);
const permalink = computed(() => {
  if (currentDandiset.value?.dandiset && currentVersion.value) {
    return `${window.location.origin}/dandiset/${currentDandiset.value?.dandiset.identifier}/${currentVersion.value}`;
  }
  return '';
});
const doiLink = computed(() => (currentDandiset.value?.version !== 'draft' ? `https://doi.org/${meta.value?.doi}` : ''));
</script>
