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
import { computed, onMounted, ref } from 'vue';
import { downloadZip } from 'client-zip';
import { filesize } from 'filesize';
import { useDandisetStore } from '@/stores/dandiset';
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

const zipInProgress = ref(false);
const zipProgress = ref(0); // 0–100
const zipError = ref('');
const zipCanceled = ref(false);

let zipAbortController: AbortController | null = null;

function cancelZip() {
  zipAbortController?.abort();
}

// Wrap a byte stream so we can count bytes as they flow through to the zipper,
// giving smooth progress even when a dandiset is a few large files.
function trackStream(
  stream: ReadableStream<Uint8Array>,
  onBytes: (n: number) => void,
): ReadableStream<Uint8Array> {
  const reader = stream.getReader();
  return new ReadableStream<Uint8Array>({
    async pull(controller) {
      const { done, value } = await reader.read();
      if (done) {
        controller.close();
        return;
      }
      onBytes(value.byteLength);
      controller.enqueue(value);
    },
    cancel(reason) {
      reader.cancel(reason);
    },
  });
}

const browserZipEligible = computed(() => {
  const version = currentDandiset.value;
  return !!version
    && !!identifier.value
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

  zipInProgress.value = true;
  zipProgress.value = 0;
  zipError.value = '';
  zipCanceled.value = false;
  zipAbortController = new AbortController();
  const { signal } = zipAbortController;

  try {
    const allAssets = await fetchAllAssets(id, version, signal);
    // Zarr assets aren't single blobs and can't be fetched via the download endpoint.
    const blobAssets = allAssets.filter((a) => !a.zarr);
    const skipped = allAssets.length - blobAssets.length;
    if (blobAssets.length === 0) {
      zipError.value = 'No downloadable files in this dandiset (Zarr assets are not supported).';
      return;
    }

    const totalBytes = blobAssets.reduce((sum, a) => sum + a.size, 0);
    let downloadedBytes = 0;

    // Nest everything under a single root folder matching the zip filename.
    const rootFolder = `${id}-${version}`;

    // Lazily fetch each asset so only one file is in flight at a time.
    async function* zipEntries() {
      for (const asset of blobAssets) {
        const url = dandiRest.assetDownloadURI(id!, version!, asset.asset_id);
        const response = await fetch(url, { signal });
        if (!response.ok) {
          throw new Error(`Failed to download "${asset.path}" (HTTP ${response.status})`);
        }
        const body = response.body
          ? trackStream(response.body, (n) => {
            downloadedBytes += n;
            zipProgress.value = totalBytes ? (downloadedBytes / totalBytes) * 100 : 0;
          })
          : response;
        yield {
          name: `${rootFolder}/${asset.path}`,
          input: body,
          size: asset.size,
          lastModified: new Date(asset.modified),
        };
      }
    }

    const zipResponse = downloadZip(zipEntries(), { length: blobAssets.length });
    const blob = await zipResponse.blob();

    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = objectUrl;
    link.download = `${rootFolder}.zip`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(objectUrl);

    if (skipped > 0) {
      zipError.value = `Downloaded ${blobAssets.length} files. Skipped ${skipped} Zarr asset(s) — use the DANDI CLI for those.`;
    }
  } catch (err) {
    if (signal.aborted) {
      zipCanceled.value = true;
      zipError.value = 'Download canceled.';
    } else {
      zipError.value = err instanceof Error ? err.message : 'Download failed.';
    }
  } finally {
    zipInProgress.value = false;
    zipAbortController = null;
  }
}
</script>
