<template>
  <v-menu
    :close-on-content-click="false"
    min-width="500"
    max-width="500"
  >
    <template #activator="{ props }">
      <v-list-item
        id="download"
        class="justify-space-between border border-b-0 rounded-t"
        v-bind="props"
      >
        <template #prepend>
          <v-icon
            color="primary"
            start
          >
            mdi-download
          </v-icon>
          <v-list-item-title>Download</v-list-item-title>
        </template>
        <template #append>
          <v-icon end>
            mdi-chevron-down
          </v-icon>
        </template>
      </v-list-item>
    </template>
    <v-card>
      <v-card-title>
        Download full dandiset
        <v-spacer />
        <v-tooltip location="right">
          <template #activator="{ props }">
            <v-btn
              :href="`${dandiDocumentationUrl}/user-guide-using/accessing-data/downloading`"
              target="_blank"
              rel="noopener"
              variant="text"
            >
              Help
              <v-icon
                color="primary"
                size="small"
                v-bind="props"
              >
                mdi-help-circle
              </v-icon>
            </v-btn>
          </template>
          More help on download
        </v-tooltip>
      </v-card-title>
      <v-list class="pa-0">
        <!-- PROTOTYPE: in-browser zip download for small dandisets -->
        <template v-if="browserZipEligible">
          <v-list-item density="compact">
            Download directly in your browser
            ({{ filesize(currentDandiset?.size ?? 0, { round: 1, base: 10, standard: 'si' }) }})
          </v-list-item>
          <template v-if="zipInProgress">
            <v-list-item density="compact">
              <v-progress-linear
                :model-value="zipProgress"
                :indeterminate="zipProgress === 0"
                color="primary"
                height="20"
                rounded
              >
                <span class="text-caption">{{ Math.round(zipProgress) }}%</span>
              </v-progress-linear>
            </v-list-item>
            <v-list-item density="compact">
              <v-btn
                color="error"
                variant="outlined"
                block
                prepend-icon="mdi-close"
                @click="cancelZip"
              >
                Cancel
              </v-btn>
            </v-list-item>
            <v-list-item density="compact">
              <em>Leaving this Dandiset page or changing versions will cancel the download</em>
            </v-list-item>
          </template>
          <v-list-item
            v-else
            density="compact"
          >
            <v-btn
              color="primary"
              variant="flat"
              block
              prepend-icon="mdi-folder-zip"
              @click="downloadAsZip"
            >
              Download .zip
            </v-btn>
          </v-list-item>
          <v-list-item
            v-if="zipError"
            density="compact"
            :class="zipCanceled ? 'text-medium-emphasis text-caption' : 'text-error text-caption'"
          >
            {{ zipError }}
          </v-list-item>
          <v-divider class="my-2" />
        </template>
        <v-list-item density="compact">
          Use this command in your DANDI CLI
        </v-list-item>
        <v-list-item density="compact">
          <CopyText
            :text="defaultDownloadText"
            icon-hover-text="Copy command to clipboard"
            dense
            filled
            outlined
          />
        </v-list-item>
        <v-expansion-panels>
          <v-expansion-panel v-if="availableVersions.length > 0">
            <v-expansion-panel-title>
              Download a different version?
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <v-list class="pa-0">
                <v-list-item density="compact">
                  <v-radio-group v-model="selectedDownloadOption">
                    <v-radio
                      label="Draft"
                      value="draft"
                    />
                    <v-radio
                      label="Latest version"
                      value="latest"
                    />
                    <v-radio
                      label="Other version"
                      value="other"
                    />
                    <v-select
                      v-if="selectedDownloadOption == 'other'"
                      v-model="selectedVersion"
                      :items="availableVersions"
                      item-title="version"
                      item-value="index"
                      density="compact"
                    />
                  </v-radio-group>
                </v-list-item>
                <v-list-item density="compact">
                  <CopyText
                    :text="customDownloadText"
                    icon-hover-text="Copy command to clipboard"
                    color="primary"
                    dense
                    outlined
                    filled
                  />
                </v-list-item>
              </v-list>
            </v-expansion-panel-text>
          </v-expansion-panel>
          <v-expansion-panel>
            <v-expansion-panel-title>
              Don't have DANDI CLI?
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <v-list>
                <v-list-item>
                  Install the Python client (DANDI CLI)
                  in a Python {{ cliRequiresPython }} environment using command:
                </v-list-item>
                <v-list-item>
                  <kbd>pip install "dandi>={{ cliMinimalVersion }}"</kbd>
                </v-list-item>
              </v-list>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-list>
    </v-card>
  </v-menu>
</template>
<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { filesize } from 'filesize';
import { useDandisetStore } from '@/stores/dandiset';
import { useZipDownload, type ZipEntry } from '@/composables/useZipDownload';
import CopyText from '@/components/CopyText.vue';
import { dandiDocumentationUrl } from '@/utils/constants';
import { dandiRest } from '@/rest';
import type { Asset } from '@/types';

// In-browser zip is gated to "small" dandisets: the whole archive is buffered in
// memory (client-zip -> Blob) before the browser saves it, so keep both bytes and
// file-count conservative. Bump these once a streaming-to-disk path is added.
const BROWSER_ZIP_MAX_SIZE = 2 * (1024 ** 3); // 2 GiB
const BROWSER_ZIP_MAX_FILES = 1000;

// The assets list endpoint returns `zarr`/`blob` slugs that aren't on the TS Asset type.
type AssetWithStorage = Asset & { zarr: string | null; blob: string | null };

function downloadCommand(identifier: string, version: string): string {
  // Use the special 'DANDI:' url prefix if appropriate.
  const generalUrl = `${window.location.origin}/dandiset/${identifier}`;
  const dandiUrl = `DANDI:${identifier}`;
  const url = window.location.origin == 'https://dandiarchive.org' ? dandiUrl : generalUrl;

  // Prepare a url suffix to specify a specific version (or not).
  const versionPath = version ? `/${version}` : '';

  return `dandi download ${url}${versionPath}`;
}

const store = useDandisetStore();

const currentDandiset = computed(() => store.dandiset);
const publishedVersions = computed(() => store.versions);
const currentVersion = computed(() => store.version);

const cliMinimalVersion = ref<string>();
const cliRequiresPython = ref<string>();
onMounted(async () => {
  const info = await dandiRest.info();
  cliMinimalVersion.value = info['cli-minimal-version'];
  cliRequiresPython.value = info['cli-requires-python'];
});

const selectedDownloadOption = ref('draft');
const selectedVersion = ref(0);

const identifier = computed(() => currentDandiset.value?.dandiset.identifier);

const availableVersions = computed(
  () => (publishedVersions.value || [])
    .map((version, index) => ({ version: version.version, index })),
);

const defaultDownloadText = computed(
  () => (identifier.value ? downloadCommand(identifier.value, currentVersion.value) : ''),
);

const customDownloadText = computed(() => {
  if (!identifier.value) {
    return '';
  }
  if (selectedDownloadOption.value === 'draft') {
    return downloadCommand(identifier.value, 'draft');
  } if (selectedDownloadOption.value === 'latest') {
    return downloadCommand(identifier.value, '');
  } if (selectedDownloadOption.value === 'other') {
    return downloadCommand(
      identifier.value,
      availableVersions.value[selectedVersion.value].version,
    );
  }
  return '';
});

// --- In-browser zip download (prototype) ---------------------------------

const {
  inProgress: zipInProgress,
  progress: zipProgress,
  canceled: zipCanceled,
  cancel: cancelZip,
  download: downloadEntriesAsZip,
} = useZipDownload();

onUnmounted(() => {
  cancelZip();
});

watch([identifier, currentVersion], () => cancelZip());

const zipError = ref('');

const browserZipEligible = computed(() => {
  const version = currentDandiset.value;
  // The composable fetches assets without auth headers, so embargoed
  // dandisets (which require an authenticated download) are excluded.
  return !!version
    && !!identifier.value
    && version.dandiset.embargo_status === 'OPEN'
    && version.size > 0
    && version.size <= BROWSER_ZIP_MAX_SIZE
    && version.asset_count > 0
    && version.asset_count <= BROWSER_ZIP_MAX_FILES;
});

// Fetch every asset in the version, following pagination.
async function fetchAllAssets(
  id: string,
  version: string,
  signal: AbortSignal,
): Promise<AssetWithStorage[]> {
  const assets: AssetWithStorage[] = [];
  let page = 1;
  for (;;) {
    const data = await dandiRest.assets(id, version, { params: { page, page_size: 1000 }, signal });
    if (page === 1 && data === null) {
      throw new Error('Failed to fetch assets for the current Dandiset');
    }
    if (!data) {
      break;
    }
    assets.push(...(data.results as unknown as AssetWithStorage[]));
    if (!data.next) {
      break;
    }
    page += 1;
  }
  return assets;
}

async function downloadAsZip() {
  const id = identifier.value;
  const version = currentVersion.value;
  if (!id || !version || zipInProgress.value) {
    return;
  }

  zipError.value = '';

  // Nest everything under a single root folder matching the zip filename.
  const rootFolder = `${id}-${version}`;
  let included = 0;
  let skipped = 0;

  try {
    await downloadEntriesAsZip(`${rootFolder}.zip`, async (signal): Promise<ZipEntry[]> => {
      const allAssets = await fetchAllAssets(id, version, signal);
      // Zarr assets aren't single blobs and can't be fetched via the download endpoint.
      const blobAssets = allAssets.filter((a) => !a.zarr);
      included = blobAssets.length;
      skipped = allAssets.length - blobAssets.length;
      if (blobAssets.length === 0) {
        throw new Error('No downloadable files in this dandiset (Zarr assets are not supported).');
      }
      return blobAssets.map((asset) => ({
        name: `${rootFolder}/${asset.path}`,
        url: dandiRest.assetDownloadURI(id, version, asset.asset_id),
        size: asset.size,
        lastModified: new Date(asset.modified),
      }));
    });

    if (skipped > 0) {
      zipError.value = `Downloaded ${included} files. Skipped ${skipped} Zarr asset(s); use the DANDI CLI for those.`;
    }
  } catch (err) {
    if (zipCanceled.value) {
      zipError.value = 'Download canceled.';
    } else {
      zipError.value = err instanceof Error ? err.message : 'Download failed.';
    }
  }
}
</script>
