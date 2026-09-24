<template>
  <v-dialog
    v-model="open"
    max-width="90vw"
    scrollable
  >
    <v-card v-if="item">
      <v-card-title class="d-flex align-center">
        <v-icon
          class="mr-2"
          color="primary"
        >
          mdi-table
        </v-icon>
        <span
          class="text-truncate"
          :title="item.path"
        >{{ name }}</span>
        <v-spacer />
        <v-tooltip
          v-if="rawText"
          location="bottom"
        >
          <template #activator="{ props: rawProps }">
            <v-btn
              icon
              variant="text"
              v-bind="rawProps"
              @click="showRaw = !showRaw"
            >
              <v-icon color="primary">
                {{ showRaw ? 'mdi-table' : 'mdi-file-document-outline' }}
              </v-icon>
            </v-btn>
          </template>
          <span>{{ showRaw ? 'View as table' : 'View raw text' }}</span>
        </v-tooltip>
        <v-tooltip location="bottom">
          <template #activator="{ props: downloadProps }">
            <v-btn
              icon
              variant="text"
              :href="downloadUri"
              v-bind="downloadProps"
            >
              <v-icon color="primary">
                mdi-download
              </v-icon>
            </v-btn>
          </template>
          <span>Download asset</span>
        </v-tooltip>
        <v-btn
          icon
          variant="text"
          @click="open = false"
        >
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-divider />

      <v-progress-linear
        v-if="loading"
        indeterminate
      />

      <v-card-text class="viewer-body">
        <v-alert
          v-if="error"
          type="error"
          variant="tonal"
        >
          {{ error }}
        </v-alert>

        <pre
          v-else-if="!loading && showRaw"
          class="raw-text"
        >{{ rawText }}</pre>

        <template v-else-if="!loading">
          <v-alert
            v-if="truncated"
            type="info"
            variant="tonal"
            density="compact"
            class="mb-3"
          >
            This file is large, so only the first {{ rows.length }} rows are shown.
            Download the file to see its full contents.
          </v-alert>

          <div class="d-flex align-center mb-2">
            <v-text-field
              v-model="search"
              label="Search table"
              prepend-inner-icon="mdi-magnify"
              density="compact"
              variant="outlined"
              hide-details
              clearable
              style="max-width: 20em;"
            />
            <v-spacer />
            <span class="text-caption text-medium-emphasis">
              {{ dataRows.length }} rows &times; {{ columnCount }} columns
            </span>
          </div>

          <v-data-table
            v-if="dataRows.length"
            :headers="headers"
            :items="tableItems"
            :search="search"
            :items-per-page="25"
            density="compact"
            class="table-viewer"
            fixed-header
          >
            <template
              v-for="header in headers"
              #[`item.${header.key}`]="{ value }"
            >
              <a
                v-if="isUrl(value)"
                :key="header.key"
                :href="value"
                target="_blank"
                rel="noopener noreferrer"
              >{{ value }}</a>
              <template v-else>
                {{ value }}
              </template>
            </template>
          </v-data-table>
          <v-banner v-else>
            This file is empty.
          </v-banner>
        </template>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import type { Ref } from 'vue';
import { computed, ref, watch } from 'vue';
import axios from 'axios';

import type { AssetPath } from '@/types';
import { dandiRest } from '@/rest';
import { useDandisetStore } from '@/stores/dandiset';
import type { Delimiter } from '@/utils/tabular';
import { isUrl, parseDelimitedText, tabularDelimiter } from '@/utils/tabular';

// Guardrails, so that a pathologically large file can't lock up the browser.
const MAX_FILE_SIZE = 50e6;
const MAX_ROWS = 5000;

const props = defineProps<{
  modelValue: boolean,
  item: AssetPath | null,
  identifier: string,
  version: string,
}>();

const emit = defineEmits<{(e: 'update:modelValue', value: boolean): void}>();

const open = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
});

const store = useDandisetStore();

const loading = ref(false);
const error: Ref<string | null> = ref(null);
const rows: Ref<string[][]> = ref([]);
const truncated = ref(false);
const search = ref('');
// The file's text as fetched, shown by the raw-text toggle. The row cap below
// applies to the table only, so this stays the complete contents.
const rawText = ref('');
const showRaw = ref(false);

const name = computed(() => props.item?.path.split('/').pop() || '');
const assetId = computed(() => props.item?.asset?.asset_id || null);
const inlineUri = computed(() => (
  assetId.value ? dandiRest.assetInlineURI(props.identifier, props.version, assetId.value) : ''
));
const downloadUri = computed(() => (
  assetId.value ? dandiRest.assetDownloadURI(props.identifier, props.version, assetId.value) : ''
));

// Mirrors the URL choice made for external services: the direct S3 link is
// fetchable cross-origin, but embargoed assets have to go through the API.
const embargoed = computed(
  () => store.dandiset?.dandiset.embargo_status === 'EMBARGOED',
);
const fetchUri = computed(() => {
  const s3Url = props.item?.asset?.url;
  return (!embargoed.value && s3Url) ? s3Url : inlineUri.value;
});

const columnCount = computed(
  () => rows.value.reduce((max, row) => Math.max(max, row.length), 0),
);
// The first row is always treated as the header row.
const dataRows = computed(() => rows.value.slice(1));
const headers = computed(() => {
  const headerRow = rows.value[0] || [];
  return Array.from({ length: columnCount.value }, (_, i) => ({
    title: headerRow[i] || `Column ${i + 1}`,
    key: `c${i}`,
  }));
});
const tableItems = computed(() => dataRows.value.map(
  (row) => Object.fromEntries(
    Array.from({ length: columnCount.value }, (_, i) => [`c${i}`, row[i] ?? '']),
  ),
));

async function loadFile() {
  const { item } = props;
  if (!item?.asset) {
    return;
  }

  const delimiter: Delimiter | null = tabularDelimiter(item.path);
  if (delimiter === null) {
    error.value = 'This file is not a supported tabular file.';
    return;
  }

  loading.value = true;
  error.value = null;
  rows.value = [];
  truncated.value = false;
  search.value = '';
  rawText.value = '';
  showRaw.value = false;

  if (item.aggregate_size > MAX_FILE_SIZE) {
    error.value = 'This file is too large to preview in the browser.'
      + ' Please download it to view its contents.';
    loading.value = false;
    return;
  }

  try {
    const { data } = await axios.get<string>(fetchUri.value, {
      responseType: 'text',
      // Ensure that the response isn't parsed as JSON/XML by axios.
      transformResponse: [(response) => response],
    });
    rawText.value = data;
    const parsed = parseDelimitedText(data, delimiter);
    truncated.value = parsed.length > MAX_ROWS;
    rows.value = truncated.value ? parsed.slice(0, MAX_ROWS) : parsed;
  } catch {
    error.value = 'Failed to load this file. You can still download it.';
  } finally {
    loading.value = false;
  }
}

watch(() => [props.modelValue, props.item], () => {
  if (props.modelValue && props.item) {
    loadFile();
  }
}, { immediate: true });
</script>

<style scoped>
.viewer-body {
  max-height: 70vh;
  /* The scrollable regions below are sized to fit, so the body itself doesn't
     scroll: that keeps their horizontal scrollbars on screen. */
  overflow: hidden;
}

.table-viewer :deep(td) {
  white-space: nowrap;
}

/* Scroll the table body rather than the dialog, so that the horizontal
   scrollbar stays pinned to the bottom of the visible rows instead of sitting
   below the last row, out of view. The subtracted space covers the search row
   and the table footer. */
.table-viewer :deep(.v-table__wrapper) {
  max-height: calc(70vh - 160px);
  overflow: auto;
}

.raw-text {
  font-family: monospace;
  font-size: 0.85rem;
  /* Same reasoning as the table wrapper above. */
  max-height: calc(70vh - 48px);
  overflow: auto;
  white-space: pre;
}
</style>
