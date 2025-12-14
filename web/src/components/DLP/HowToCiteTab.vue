<template>
  <div>
    <v-card
      variant="outlined"
      class="pa-6"
    >
      <v-card-title class="d-flex align-center px-0 pt-0">
        <v-icon
          color="primary"
          class="mr-2"
        >
          mdi-format-quote-close
        </v-icon>
        How to Cite this Dataset
      </v-card-title>

      <v-card-text class="px-0">
        <v-alert
          v-if="isDraft"
          type="warning"
          variant="tonal"
          class="mb-4"
        >
          <strong>Citing draft dandisets is not recommended</strong> as the content may change.
          Please contact the authors to request publication of this dandiset.
        </v-alert>

        <p class="text-body-1 mb-4">
          To promote reproducibility and give credit to researchers who share their data,
          please acknowledge the contributors and cite this dataset in your publications.
          For more information, see our
          <a
            href="https://docs.dandiarchive.org/user-guide-using/citing-dandisets/"
            target="_blank"
            rel="noopener"
          >guide on citing dandisets</a>.
        </p>

        <!-- Citation -->
        <h3 class="text-h6 mb-2">
          Full Citation
        </h3>
        <div
          v-if="citation"
          class="copy-block mb-4"
        >
          <div class="copy-block-content">
            <span>{{ citation }}</span>
            <v-btn
              icon
              size="small"
              variant="text"
              class="copy-btn"
              @click="copyToClipboard(citation)"
            >
              <v-icon size="small">
                mdi-content-copy
              </v-icon>
              <v-tooltip
                activator="parent"
                location="top"
              >
                Copy citation to clipboard
              </v-tooltip>
            </v-btn>
          </div>
        </div>
        <p
          v-else
          class="text-body-2 font-italic mb-4"
        >
          Citation will be available after the dandiset is published.
        </p>

        <!-- DOI info for published versions -->
        <div
          v-if="doi"
          class="mb-4"
        >
          <v-chip
            :href="`https://doi.org/${doi}`"
            target="_blank"
            color="primary"
            variant="outlined"
          >
            <v-icon
              start
              size="small"
            >
              mdi-link
            </v-icon>
            DOI: {{ doi }}
          </v-chip>
        </div>

        <v-divider class="my-4" />

        <!-- Materials and Methods -->
        <h3 class="text-h6 mb-2">
          Materials and Methods
        </h3>
        <p class="text-body-2 mb-2">
          Suggested text for the Methods section of your manuscript:
        </p>
        <div class="copy-block mb-4">
          <div class="copy-block-content">
            <span>{{ methodsText }}</span>
            <v-btn
              icon
              size="small"
              variant="text"
              class="copy-btn"
              @click="copyToClipboard(methodsText)"
            >
              <v-icon size="small">
                mdi-content-copy
              </v-icon>
              <v-tooltip
                activator="parent"
                location="top"
              >
                Copy to clipboard
              </v-tooltip>
            </v-btn>
          </div>
        </div>

        <!-- Data Availability Statement -->
        <h3 class="text-h6 mb-2">
          Data Availability Statement
        </h3>
        <p class="text-body-2 mb-2">
          Suggested statement for your manuscript:
        </p>
        <div class="copy-block mb-4">
          <div class="copy-block-content">
            <span>{{ dataAvailabilityText }}</span>
            <v-btn
              icon
              size="small"
              variant="text"
              class="copy-btn"
              @click="copyToClipboard(dataAvailabilityText)"
            >
              <v-icon size="small">
                mdi-content-copy
              </v-icon>
              <v-tooltip
                activator="parent"
                location="top"
              >
                Copy to clipboard
              </v-tooltip>
            </v-btn>
          </div>
        </div>

        <v-divider class="my-4" />

        <!-- DANDI Identifier -->
        <h3 class="text-h6 mb-2">
          DANDI Identifier
        </h3>
        <div class="copy-block mb-2">
          <div class="copy-block-content copy-block-inline">
            <span>{{ dandiIdentifier }}</span>
            <v-btn
              icon
              size="small"
              variant="text"
              class="copy-btn"
              @click="copyToClipboard(dandiIdentifier)"
            >
              <v-icon size="small">
                mdi-content-copy
              </v-icon>
              <v-tooltip
                activator="parent"
                location="top"
              >
                Copy identifier to clipboard
              </v-tooltip>
            </v-btn>
          </div>
        </div>
        <p class="text-body-2 text-grey mb-4">
          DANDI Archive RRID: SCR_017571
        </p>

        <!-- License Information -->
        <div v-if="licenses && licenses.length">
          <h3 class="text-h6 mb-2">
            License
          </h3>
          <p class="text-body-2 mb-2">
            This dataset is shared under:
            <v-chip
              v-for="(license, i) in licenses"
              :key="i"
              class="ml-2"
              color="primary"
              variant="outlined"
              size="small"
            >
              {{ formatLicense(license) }}
            </v-chip>
          </p>
        </div>

        <v-divider class="my-4" />

        <!-- More citation formats link -->
        <p class="text-body-2 text-center">
          More citations available at:
          <a
            href="https://citation.doi.org/"
            target="_blank"
            rel="noopener"
          >
            DOI Citation Formatter
            <v-icon size="small">mdi-open-in-new</v-icon>
          </a>
        </p>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { computed, type PropType } from 'vue';

import { useDandisetStore } from '@/stores/dandiset';
import type { DandisetMetadata } from '@/types';

const props = defineProps({
  schema: {
    type: Object,
    required: true,
  },
  meta: {
    type: Object as PropType<DandisetMetadata>,
    required: true,
  },
});

const store = useDandisetStore();
const currentDandiset = computed(() => store.dandiset);
const isDraft = computed(() => store.version === 'draft');

const citation = computed(() => props.meta?.citation);
const doi = computed(() => props.meta?.doi);
const licenses = computed(() => props.meta?.license);

const dandiIdentifier = computed(() => {
  if (!currentDandiset.value) return '';
  const { identifier } = currentDandiset.value.dandiset;
  const version = props.meta?.version || currentDandiset.value.version;
  return `DANDI:${identifier}/${version}`;
});

const dandiUrl = computed(() => {
  if (doi.value) {
    return `https://doi.org/${doi.value}`;
  }
  if (!currentDandiset.value) return '';
  const { identifier } = currentDandiset.value.dandiset;
  return `https://dandiarchive.org/dandiset/${identifier}`;
});

const methodsText = computed(() => {
  const url = dandiUrl.value;
  return `Data associated with this study are available on the DANDI Archive (RRID:SCR_017571): ${url}`;
});

const dataAvailabilityText = computed(() => {
  const url = dandiUrl.value;
  return `Data are publicly available on the DANDI Archive (RRID:SCR_017571) at the following URL: ${url}`;
});

function formatLicense(license: string): string {
  // Convert spdx:CC0-1.0 to CC0 1.0, spdx:CC-BY-4.0 to CC BY 4.0, etc.
  return license
    .replace('spdx:', '')
    .replace(/-/g, ' ')
    .replace(/(\d)\.(\d)/, '$1.$2');
}

async function copyToClipboard(text: string) {
  try {
    await navigator.clipboard.writeText(text);
  } catch (err) {
    console.error('Failed to copy:', err);
  }
}
</script>

<style scoped>
.copy-block {
  background-color: #f5f5f5;
  border-radius: 4px;
  padding: 12px 16px;
}

.copy-block-content {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.copy-block-content span {
  flex: 1;
  word-break: break-word;
  line-height: 1.5;
}

.copy-block-inline {
  align-items: center;
}

.copy-btn {
  flex-shrink: 0;
}
</style>
