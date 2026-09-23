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
          mdi-language-python
        </v-icon>
        Access in Python
      </v-card-title>

      <v-card-text class="px-0">
        <p class="text-body-1 mb-4">
          <template v-if="nwbPath">
            Copy this into a notebook or script to stream an NWB file from this
            dandiset without downloading it. The code lists the dandiset's NWB
            files with the
            <a
              href="https://dandi.readthedocs.io/en/latest/modref/dandiapi.html"
              target="_blank"
              rel="noopener"
            >DANDI Python client</a>
            and opens one of them with PyNWB.
          </template>
          <template v-else>
            Copy this into a notebook or script to list and download the files in
            this dandiset with the
            <a
              href="https://dandi.readthedocs.io/en/latest/modref/dandiapi.html"
              target="_blank"
              rel="noopener"
            >DANDI Python client</a>.
          </template>
          For more examples, see the
          <a
            href="https://docs.dandiarchive.org/user-guide-using/accessing-data/"
            target="_blank"
            rel="noopener"
          >guide to accessing data</a>.
        </p>

        <v-progress-linear
          v-if="loading"
          indeterminate
          color="primary"
        />
        <div
          v-else
          class="code-block"
        >
          <pre class="code-text">{{ code }}</pre>
          <v-btn
            icon
            size="small"
            variant="text"
            class="copy-btn"
            @click="copyCode"
          >
            <v-icon size="small">
              {{ copied ? 'mdi-check' : 'mdi-content-copy' }}
            </v-icon>
            <v-tooltip
              activator="parent"
              location="top"
            >
              Copy code to clipboard
            </v-tooltip>
          </v-btn>
        </div>

        <p
          v-if="!loading && neurosiftUrl"
          class="text-body-1 mt-4"
        >
          Neurosift generates a longer script for this file that shows how to
          read each of its objects, with their shapes and descriptions:
          <a
            :href="neurosiftUrl"
            target="_blank"
            rel="noopener"
          >Python usage for this file in Neurosift</a>.
          To get the same for another file, open it in Neurosift from the file
          browser and choose the Python Usage tab.
        </p>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import type { PropType } from 'vue';

import { dandiRest } from '@/rest';
import { useDandisetStore } from '@/stores/dandiset';
import type { Asset, DandisetMetadata } from '@/types';
import { pythonSnippet } from '@/utils/pythonSnippet';

defineProps({
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

const loading = ref(true);
const nwbAsset = ref<Asset | null>(null);
const nwbPath = computed(() => nwbAsset.value?.path ?? null);
const anyPath = ref<string | null>(null);
const copied = ref(false);

async function firstAsset(identifier: string, version: string, glob?: string) {
  const params: Record<string, string | number> = { page_size: 1 };
  if (glob) {
    params.glob = glob;
  }
  const page = await dandiRest.assets(identifier, version, { params });
  return page?.results[0] ?? null;
}

watch(
  () => [currentDandiset.value?.dandiset.identifier, currentDandiset.value?.version] as const,
  async ([identifier, version]) => {
    if (!identifier || !version) {
      return;
    }
    loading.value = true;
    let nwb: Asset | null = null;
    let any: string | null = null;
    try {
      nwb = await firstAsset(identifier, version, '*.nwb');
      any = nwb?.path ?? (await firstAsset(identifier, version))?.path ?? null;
    } catch (err) {
      console.error('Failed to fetch an example asset:', err);
    }
    if (currentDandiset.value?.dandiset.identifier === identifier
      && currentDandiset.value?.version === version) {
      nwbAsset.value = nwb;
      anyPath.value = any;
      loading.value = false;
    }
  },
  { immediate: true },
);

const code = computed(() => {
  const dandiset = currentDandiset.value;
  if (!dandiset) {
    return '';
  }
  return pythonSnippet({
    identifier: dandiset.dandiset.identifier,
    version: dandiset.version,
    apiRoot: import.meta.env.VITE_APP_DANDI_API_ROOT,
    embargoed: dandiset.dandiset.embargo_status !== 'OPEN',
    nwbPath: nwbPath.value,
    anyPath: anyPath.value,
  });
});

// Neurosift's NWB page opens directly on its generated usage script with ?tab=python-usage.
const neurosiftUrl = computed(() => {
  const dandiset = currentDandiset.value;
  if (!dandiset || !nwbAsset.value) {
    return null;
  }
  const { identifier } = dandiset.dandiset;
  const params = new URLSearchParams({
    url: dandiRest.assetDownloadURI(identifier, dandiset.version, nwbAsset.value.asset_id),
    dandisetId: identifier,
    dandisetVersion: dandiset.version,
    tab: 'python-usage',
  });
  return `https://neurosift.app/nwb?${params}`;
});

async function copyCode() {
  try {
    await navigator.clipboard.writeText(code.value);
    copied.value = true;
    window.setTimeout(() => {
      copied.value = false;
    }, 2000);
  } catch (err) {
    console.error('Failed to copy:', err);
  }
}
</script>

<style scoped>
.code-block {
  position: relative;
  background-color: #f5f5f5;
  border-radius: 4px;
  padding: 16px;
}

.code-text {
  margin: 0;
  padding-right: 40px;
  overflow-x: auto;
  font-family: 'Roboto Mono', monospace;
  font-size: 0.875rem;
  line-height: 1.5;
}

.copy-btn {
  position: absolute;
  top: 8px;
  right: 8px;
}
</style>
