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
          v-if="isDraft && hasPublishedVersions"
          type="warning"
          variant="tonal"
          class="mb-4"
        >
          <strong>Citing draft dandisets is not recommended</strong> as the content may change.
          Please cite the
          <router-link :to="latestPublishedVersionLink">
            latest published version ({{ latestPublishedVersion }})
          </router-link>
          instead.
        </v-alert>

        <v-alert
          v-else-if="isDraft"
          type="warning"
          variant="tonal"
          class="mb-4"
        >
          <strong>Citing draft dandisets is not recommended</strong> as the content may change.
          Please contact the authors to request publication of this dandiset before citing.
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
        <div class="d-flex align-center mb-2">
          <h3 class="text-h6 mr-4">
            Full Citation
          </h3>
          <v-select
            v-model="selectedCitationFormat"
            :items="citationFormats"
            item-title="text"
            item-value="value"
            variant="outlined"
            density="compact"
            hide-details
            class="citation-format-select"
          />
        </div>
        <div class="copy-block mb-4">
          <div class="copy-block-content">
            <pre v-if="isCodeFormat" class="citation-text-code">{{ currentCitation }}</pre>
            <span v-else class="citation-text">{{ currentCitation }}</span>
            <v-btn
              icon
              size="small"
              variant="text"
              class="copy-btn"
              @click="copyToClipboard(currentCitation)"
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

      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { computed, type PropType, ref } from 'vue';

import { useDandisetStore } from '@/stores/dandiset';
import type { DandisetMetadata } from '@/types';
import { dandisetToCFF, cffToBibTeX, cffToAPA, cffToMLA, cffToChicago, cffToHarvard, cffToVancouver, cffToIEEE, cffToRIS, cffToYAML } from '@/utils/cff';

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
const publishedVersions = computed(() => store.publishedVersions);
const hasPublishedVersions = computed(() => publishedVersions.value && publishedVersions.value.length > 0);
const latestPublishedVersion = computed(() => {
  if (!publishedVersions.value || publishedVersions.value.length === 0) {
    return null;
  }

  // Versions are sorted, so the first one is the latest
  return publishedVersions.value[0].version;
});
const latestPublishedVersionLink = computed(() => {
  if (!currentDandiset.value || !latestPublishedVersion.value) {
    return '';
  }

  const { identifier } = currentDandiset.value.dandiset;
  return `/dandiset/${identifier}/${latestPublishedVersion.value}`;
});

// Define citation format types
type CitationFormat = 'apa' | 'mla' | 'chicago' | 'harvard' | 'vancouver' | 'ieee' | 'bibtex' | 'ris' | 'cff';

// Citation format state
const selectedCitationFormat = ref<CitationFormat>('apa'); // For the dropdown in Full Citation section

// Generate CFF object from metadata
const cffObject = computed(() => {
  if (!props.meta) {
    return null;
  }

  return dandisetToCFF(props.meta, typeof doi.value === 'string' ? doi.value : undefined);
});

// Generate citations in different formats
const formattedCitations = computed<Record<CitationFormat, string>>(() => {
  if (!cffObject.value || !currentDandiset.value) {
    return {
      apa: '',
      mla: '',
      chicago: '',
      harvard: '',
      vancouver: '',
      ieee: '',
      bibtex: '',
      ris: '',
      cff: '',
    };
  }
  const identifier = dandiIdentifier.value;

  return {
    apa: cffToAPA(cffObject.value),
    mla: cffToMLA(cffObject.value),
    chicago: cffToChicago(cffObject.value),
    harvard: cffToHarvard(cffObject.value),
    vancouver: cffToVancouver(cffObject.value),
    ieee: cffToIEEE(cffObject.value),
    bibtex: cffToBibTeX(cffObject.value, identifier),
    ris: cffToRIS(cffObject.value, identifier),
    cff: cffToYAML(cffObject.value),
  };
});

const citationFormats: Array<{ value: CitationFormat; text: string; icon: string }> = [
  { value: 'apa', text: 'APA 7th', icon: 'mdi-format-text' },
  { value: 'mla', text: 'MLA 9th', icon: 'mdi-format-text' },
  { value: 'chicago', text: 'Chicago', icon: 'mdi-format-text' },
  { value: 'harvard', text: 'Harvard', icon: 'mdi-format-text' },
  { value: 'vancouver', text: 'Vancouver', icon: 'mdi-format-text' },
  { value: 'ieee', text: 'IEEE', icon: 'mdi-format-text' },
  { value: 'bibtex', text: 'BibTeX', icon: 'mdi-code-braces' },
  { value: 'ris', text: 'RIS', icon: 'mdi-file-export' },
  { value: 'cff', text: 'CFF (YAML)', icon: 'mdi-file-code' },
];

const citation = computed(() => props.meta?.citation);
const doi = computed(() => props.meta?.doi);
const licenses = computed(() => props.meta?.license);

// Current citation based on selected format
const currentCitation = computed(() => {
  // For published versions with a citation, allow format selection
  if (citation.value && formattedCitations.value[selectedCitationFormat.value]) {
    return formattedCitations.value[selectedCitationFormat.value];
  }

  // Default to the original citation value
  return citation.value;
});

// Check if the selected format is a code-like format that needs preformatted text
const isCodeFormat = computed(() => {
  return ['bibtex', 'ris', 'cff'].includes(selectedCitationFormat.value);
});

const dandiIdentifier = computed(() => {
  if (!currentDandiset.value) {
    return '';
  }

  const { identifier } = currentDandiset.value.dandiset;
  const version = props.meta?.version || currentDandiset.value.version;
  return `DANDI:${identifier}/${version}`;
});

const dandiUrl = computed(() => {
  if (doi.value) {
    return `https://doi.org/${doi.value}`;
  }
  if (!currentDandiset.value) {
    return '';
  }

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

.citation-preview {
  position: relative;
  background-color: #f5f5f5;
  border-radius: 4px;
  padding: 16px;
  padding-top: 32px;
}

.citation-preview pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: 'Roboto Mono', monospace;
  font-size: 0.875rem;
  line-height: 1.5;
}

.copy-preview-btn {
  position: absolute;
  top: 8px;
  right: 8px;
}

.citation-format-select {
  max-width: 200px;
  min-width: 150px;
}

.citation-text {
  flex: 1;
  word-break: break-word;
  line-height: 1.5;
}

.citation-text-code {
  flex: 1;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: 'Roboto Mono', monospace;
  font-size: 0.875rem;
  line-height: 1.5;
  background: transparent;
  padding: 0;
}
</style>
