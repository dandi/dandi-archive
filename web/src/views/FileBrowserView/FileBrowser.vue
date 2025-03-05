<template>
  <div v-if="!unembargo_in_progress">
    <v-progress-linear
      v-if="!currentDandiset"
      indeterminate
    />
    <v-container v-else>
      <v-dialog
        v-if="!!itemToDelete"
        v-model="itemToDelete"
        persistent
        max-width="60vh"
      >
        <v-card>
          <v-card-title class="text-h5">
            Really delete this asset?
          </v-card-title>

          <v-card-text>
            Are you sure you want to delete asset <span
              class="font-italic"
            >{{ itemToDelete.path }}</span>?
            <strong>This action cannot be undone.</strong>
          </v-card-text>

          <v-card-actions>
            <v-spacer />
            <v-btn
              @click="itemToDelete = null"
            >
              Cancel
            </v-btn>
            <v-btn
              v-if="itemToDelete"
              color="error"
              @click="deleteAsset"
            >
              Yes
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>

      <v-row>
        <v-col :cols="12">
          <v-card>
            <v-card-title class="d-flex align-center">
              <v-btn
                icon
                exact
                :to="{
                  name: 'dandisetLanding',
                  params: { identifier, version },
                }"
              >
                <v-icon>mdi-home</v-icon>
              </v-btn>
              <v-divider
                vertical
                class="ml-2 mr-3"
              />
              <router-link
                :to="{ name: 'fileBrowser', query: { location: rootDirectory } }"
                exact
                style="text-decoration: none;"
                class="mx-2"
              >
                {{ identifier }}
              </router-link>

              <template v-for="(part, i) in splitLocation">
                <template v-if="part">
                  /
                  <router-link
                    :key="part"
                    :to="{ name: 'fileBrowser', query: { location: locationSlice(i) } }"
                    exact
                    style="text-decoration: none;"
                    class="mx-2"
                  >
                    {{ part }}
                  </router-link>
                </template>
              </template>
              <span class="ml-auto">
                <b>Size</b>
              </span>
            </v-card-title>
            <v-progress-linear
              v-if="updating"
              indeterminate
            />

            <v-divider v-else />

            <FileUploadInstructions v-if="currentDandiset.asset_count === 0" />
            <v-banner v-else-if="itemsNotFound">
              No items found at the specified path.
            </v-banner>
            <v-list v-else>
              <!-- Extra item to navigate up the tree -->
              <v-list-item
                v-if="location !== rootDirectory"
                @click="navigateToParent"
              >
                <template #prepend>
                  <v-icon
                    class="mr-2"
                    color="primary"
                  >
                    mdi-folder
                  </v-icon>
                  ..
                </template>
              </v-list-item>

              <v-list-item
                v-for="item in items"
                :key="item.path"
                color="primary"
                @click="openItem(item)"
              >
                <template #prepend>
                  <v-icon
                    class="mr-2"
                    color="primary"
                  >
                    <template v-if="item.asset === null">
                      mdi-folder
                    </template>
                    <template v-else>
                      mdi-file
                    </template>
                  </v-icon>
                  {{ item.name }}
                </template>

                <template #append>
                  <v-list-item-action>
                    <v-btn
                      v-if="showDelete(item)"
                      icon
                      @click="setItemToDelete(item)"
                    >
                      <v-icon color="error">
                        mdi-delete
                      </v-icon>
                    </v-btn>
                  </v-list-item-action>

                  <v-list-item-action v-if="item.asset">
                    <v-tooltip location="top">
                      <template #activator="{ props: openInBtnProps }">
                        <v-btn
                          icon
                          :href="inlineURI(item.asset.asset_id)"

                          v-bind="openInBtnProps"
                        >
                          <v-icon color="primary">
                            mdi-open-in-app
                          </v-icon>
                        </v-btn>
                      </template>
                      <span>Open asset in browser (you can also click on the item itself)</span>
                    </v-tooltip>
                  </v-list-item-action>

                  <v-list-item-action v-if="item.asset">
                    <v-tooltip location="top">
                      <template #activator="{ props: downloadProps }">
                        <v-btn
                          icon
                          :href="downloadURI(item.asset.asset_id)"

                          v-bind="downloadProps"
                        >
                          <v-icon color="primary">
                            mdi-download
                          </v-icon>
                        </v-btn>
                      </template>
                      <span>Download asset</span>
                    </v-tooltip>
                  </v-list-item-action>

                  <v-list-item-action v-if="item.asset">
                    <v-tooltip location="top">
                      <template #activator="{ props: infoProps }">
                        <v-btn
                          icon
                          :href="assetMetadataURI(item.asset.asset_id)"
                          target="_blank"
                          rel="noreferrer"

                          v-bind="infoProps"
                        >
                          <v-icon color="primary">
                            mdi-information
                          </v-icon>
                        </v-btn>
                      </template>
                      <span>View asset metadata</span>
                    </v-tooltip>
                  </v-list-item-action>

                  <v-list-item-action v-if="item.asset">
                    <v-menu
                      location="bottom left"
                    >
                      <template #activator="{ props: openWithProps }">
                        <v-btn
                          color="primary"
                          size="x-small"
                          :disabled="!item.services || !item.services.length"

                          v-bind="openWithProps"
                        >
                          Open With <v-icon size="small">
                            mdi-menu-down
                          </v-icon>
                        </v-btn>
                      </template>
                      <v-list
                        v-if="item && item.services"
                        density="compact"
                      >
                        <v-list-subheader
                          v-if="item.services.length"
                          class="font-weight-medium"
                        >
                          EXTERNAL SERVICES
                        </v-list-subheader>

                        <v-list-item
                          v-for="el in item.services"
                          :key="el.name"
                          :href="el.url"
                          target="_blank"
                          rel="noreferrer"
                        >
                          <v-list-item-title class="font-weight-light">
                            {{ el.name }}
                          </v-list-item-title>
                        </v-list-item>
                      </v-list>
                    </v-menu>
                  </v-list-item-action>

                  <v-list-item-action
                    v-if="item.aggregate_size"
                    class="justify-end"
                    :style="{width: '4.5em'}"
                  >
                    {{ fileSize(item) }}
                  </v-list-item-action>
                </template>
              </v-list-item>
            </v-list>
          </v-card>
        </v-col>
      </v-row>
      <FileBrowserPagination
        v-if="currentDandiset.asset_count"
        :page="page"
        :page-count="pages"
        @change-page="changePage($event)"
      />
    </v-container>
  </div>
</template>

<script setup lang="ts">
import type { Ref } from 'vue';
import {
  computed, onMounted, ref, watch,
} from 'vue';
import type { RouteLocationRaw } from 'vue-router';
import { useRouter, useRoute } from 'vue-router';
import { filesize } from 'filesize';
import { trimEnd } from 'lodash';
import axios from 'axios';

import { dandiRest, user } from '@/rest';
import { useDandisetStore } from '@/stores/dandiset';
import type { AssetFile, AssetPath } from '@/types';
import FileBrowserPagination from '@/components/FileBrowser/FileBrowserPagination.vue';
import FileUploadInstructions from '@/components/FileBrowser/FileUploadInstructions.vue';

const rootDirectory = '';
const FILES_PER_PAGE = 15;

// AssetService is slightly different from Service
interface AssetService {
  name: string,
  url: string,
}

interface ExtendedAssetPath extends AssetPath {
  services?: AssetService[];
  name: string;
}

const sortByFolderThenName = (a: ExtendedAssetPath, b: ExtendedAssetPath) => {
  // Sort folders first
  if (a.asset === null && b.asset !== null) {
    return -1;
  }
  if (b.asset === null && a.asset !== null) {
    return 1;
  }

  // Items are either both files or both folders
  // Sort by name
  if (a.path < b.path) {
    return -1;
  }
  if (a.path > b.path) {
    return 1;
  }

  return 0;
};

const EXTERNAL_SERVICES = [
  {
    name: 'Bioimagesuite/Viewer',
    regex: /\.nii(\.gz)?$/,
    maxsize: 1e9,
    endpoint: 'https://bioimagesuiteweb.github.io/unstableapp/viewer.html?image=$asset_url$',
  },

  {
    name: 'MetaCell/NWBExplorer',
    regex: /\.nwb$/,
    maxsize: 1e9,
    endpoint: 'http://nwbexplorer.opensourcebrain.org/nwbfile=$asset_url$',
  },

  {
    name: 'VTK/ITK Viewer',
    regex: /\.ome\.zarr$/,
    maxsize: Infinity,
    endpoint: 'https://kitware.github.io/itk-vtk-viewer/app/?gradientOpacity=0.3&image=$asset_url$',
  },

  {
    name: 'OME Zarr validator',
    regex: /\.ome\.zarr$/,
    maxsize: Infinity,
    endpoint: 'https://ome.github.io/ome-ngff-validator/?source=$asset_url$',
  },

  {
    name: 'Neurosift',
    regex: /\.nwb$/,
    maxsize: Infinity,
    endpoint: 'https://neurosift.app/nwb?url=$asset_dandi_url$&dandisetId=$dandiset_id$&dandisetVersion=$dandiset_version$',
  },

  {
    name: 'Neurosift',
    regex: /\.nwb\.lindi\.(json|tar)$/,
    maxsize: Infinity,
    endpoint: 'https://neurosift.app/nwb?url=$asset_dandi_url$&st=lindi&dandisetId=$dandiset_id$&dandisetVersion=$dandiset_version$',
  },

  {
    name: 'Neurosift',
    regex: /\.avi$/,
    maxsize: Infinity,
    endpoint: 'https://v1.neurosift.app?p=/avi&url=$asset_dandi_url$&dandisetId=$dandiset_id$&dandisetVersion=$dandiset_version$',
  }
];
type Service = typeof EXTERNAL_SERVICES[0];

const props = defineProps({
  identifier: {
    type: String,
    required: true,
  },
  version: {
    type: String,
    required: true,
  },
});

const route = useRoute();
const router = useRouter();
const store = useDandisetStore();

const location = ref(rootDirectory);
const items: Ref<ExtendedAssetPath[] | null> = ref(null);

// Value is the asset id of the item to delete
const itemToDelete: Ref<AssetPath | null> = ref(null);

const page = ref(1);
const pages = ref(0);
const updating = ref(false);

// Computed
const owners = computed(() => store.owners?.map((u) => u.username) || null);
const currentDandiset = computed(() => store.dandiset);
const embargoed = computed(() => currentDandiset.value?.dandiset.embargo_status === 'EMBARGOED');
const unembargo_in_progress = computed(() => currentDandiset.value?.dandiset.embargo_status === 'UNEMBARGOING')
const splitLocation = computed(() => location.value.split('/'));
const isAdmin = computed(() => user.value?.admin || false);
const isOwner = computed(() => !!(
  user.value && owners.value?.includes(user.value?.username)
));
const itemsNotFound = computed(() => items.value && !items.value.length);

function serviceURL(endpoint: string, data: {
  dandisetId: string,
  dandisetVersion: string,
  assetUrl: string,
  assetDandiUrl: string,
  assetS3Url: string,
}) {
  return endpoint
    .replaceAll('$dandiset_id$', data.dandisetId)
    .replaceAll('$dandiset_version$', data.dandisetVersion)
    .replaceAll('$asset_url$', data.assetUrl)
    .replaceAll('$asset_dandi_url$', data.assetDandiUrl)
    .replaceAll('$asset_s3_url$', data.assetS3Url);
}

function getExternalServices(path: AssetPath, info: {dandisetId: string, dandisetVersion: string}) {
  if (path.asset === null) {
    return [];
  }

  const servicePredicate = (service: Service, _path: AssetPath) => (
    new RegExp(service.regex).test(path.path)
          && _path.asset !== null
          && _path.aggregate_size <= service.maxsize
  );

  // Formulate the two possible asset URLs -- the direct S3 link to the relevant
  // object, and the DANDI URL that redirects to the S3 one.
  const baseApiUrl = import.meta.env.VITE_APP_DANDI_API_ROOT;
  const assetDandiUrl = `${baseApiUrl}assets/${path.asset?.asset_id}/download/`;
  const assetS3Url = trimEnd((path.asset as AssetFile).url, '/');

  // Select the best "default" URL: the direct S3 link is better when it can be
  // used, but we're forced to supply the internal DANDI URL for embargoed
  // dandisets (since the ready-made S3 URL will prevent access in that case).
  const assetUrl = embargoed.value ? assetDandiUrl : assetS3Url;

  return EXTERNAL_SERVICES
    .filter((service) => servicePredicate(service, path))
    .map((service) => ({
      name: service.name,
      url: serviceURL(service.endpoint, {
        dandisetId: info.dandisetId,
        dandisetVersion: info.dandisetVersion,
        assetUrl,
        assetDandiUrl,
        assetS3Url,
      }),
    }));
}

function locationSlice(index: number) {
  return `${splitLocation.value.slice(0, index + 1).join('/')}/`;
}

function openItem(item: AssetPath) {
  const { asset, path } = item;

  if (asset) {
    // If the item is an asset, open it in the browser.
    window.open(inlineURI(asset.asset_id), "_self");
  } else {
    // If it's a directory, move into it.
    location.value = path;
  }
}

function navigateToParent() {
  location.value = location.value.split('/').slice(0, -1).join('/');
}

function downloadURI(asset_id: string) {
  return dandiRest.assetDownloadURI(props.identifier, props.version, asset_id);
}

function inlineURI(asset_id: string) {
  return dandiRest.assetInlineURI(props.identifier, props.version, asset_id);
}

function assetMetadataURI(asset_id: string) {
  return dandiRest.assetMetadataURI(props.identifier, props.version, asset_id);
}

function fileSize(item: AssetPath) {
  return filesize(item.aggregate_size, { round: 1, base: 10, standard: 'iec' });
}

function showDelete(item: AssetPath) {
  return props.version === 'draft' && item.asset && (isAdmin.value || isOwner.value);
}

async function getItems() {
  updating.value = true;
  let resp;
  const currentPage = Number(route.query.page) || page.value;
  try {
    resp = await dandiRest.assetPaths(
      props.identifier, props.version, location.value, currentPage, FILES_PER_PAGE,
    );
  } catch (e) {
    if (axios.isAxiosError(e) && e.response?.status === 404) {
      items.value = [];
      updating.value = false;
      return;
    }
    throw e;
  }
  const { count, results } = resp;

  // Set num pages
  pages.value = Math.ceil(count / FILES_PER_PAGE);

  // Inject extra properties
  const extendedItems: ExtendedAssetPath[] = results
    .map((path) => ({
      ...path,
      // Inject relative path
      name: path.path.split('/').pop()!,
      // Inject services
      services: getExternalServices(path, {
        dandisetId: props.identifier,
        dandisetVersion: props.version,
      }) || undefined,
    }))
    .sort(sortByFolderThenName);

  // Assign values
  items.value = extendedItems;
  updating.value = false;
}

function setItemToDelete(item: AssetPath) {
  itemToDelete.value = item;
}

async function deleteAsset() {
  if (!itemToDelete.value) {
    return;
  }
  const { asset } = itemToDelete.value;
  if (asset === null) {
    throw new Error('Attempted to delete path with no asset!');
  }

  // Delete the asset on the server.
  await dandiRest.deleteAsset(props.identifier, props.version, asset.asset_id);

  // Recompute the items to display in the browser.
  getItems();
  itemToDelete.value = null;
}

// Update URL if location changes
watch(location, () => {
  const { location: existingLocation } = route.query;

  // Reset page to 1 when location changes
  page.value = 1;

  // Update route when location changes
  if (existingLocation === location.value) { return; }
  router.push({
    ...route,
    query: { location: location.value, page: String(page.value) },
  } as RouteLocationRaw);
});

// go to the directory specified in the URL if it changes
watch(() => route.query, (newRouteQuery) => {
  location.value = (
    Array.isArray(newRouteQuery.location)
      ? newRouteQuery.location[0]
      : newRouteQuery.location
  ) || rootDirectory;

  // Retrieve with new location
  getItems();
}, { immediate: true });

function changePage(newPage: number) {
  page.value = newPage;
  router.push({
    ...route,
    query: { location: location.value, page: String(page.value) },
  } as RouteLocationRaw);
}

// Fetch dandiset if necessary
onMounted(() => {
  if (!store.dandiset) {
    store.initializeDandisets({
      identifier: props.identifier,
      version: props.version,
    });
  }
});
</script>
