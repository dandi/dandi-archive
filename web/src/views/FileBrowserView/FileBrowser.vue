<template>
  <div v-if="!unembargo_in_progress">
    <v-progress-linear
      v-if="!currentDandiset"
      indeterminate
    />
    <v-container v-else>
      <v-dialog
        v-model="deletePopupOpen"
        persistent
        max-width="60vh"
      >
        <v-card v-if="itemToDelete">
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
              @click="deletePopupOpen = false"
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

      <TableViewerDialog
        :model-value="tableViewerOpen"
        :item="itemToView"
        :identifier="identifier"
        :version="version"
        @update:model-value="$event ? undefined : closeTableViewer()"
      />

      <v-row>
        <v-col :cols="12">
          <v-card>
            <v-card-title class="d-flex align-center">
              <v-btn
                icon
                variant="text"
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
                :to="locationRoute(parentLocation)"
                :active="false"
              >
                <template #prepend>
                  <v-icon
                    class="mr-2"
                    color="primary"
                  >
                    mdi-folder
                  </v-icon>
                </template>
                <v-list-item-title>..</v-list-item-title>
              </v-list-item>

              <!--
                Render each row as a real link so that
                the browser treats it as one: right click offers "Open link in new tab", and
                ctrl/cmd/middle click work as they do anywhere else. Buttons in the append
                slot stop the click and prevent its default so the row link isn't followed.
              -->
              <v-list-item
                v-for="item in items"
                :key="item.path"
                color="primary"
                v-bind="rowLink(item)"
                :active="false"
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
                </template>
                <v-list-item-title :title="item.name">
                  {{ item.name }}
                </v-list-item-title>

                <template #append>
                  <v-list-item-action>
                    <v-btn
                      v-if="showDelete(item)"
                      icon
                      variant="text"
                      @click.stop.prevent="setItemToDelete(item)"
                    >
                      <v-icon color="error">
                        mdi-delete
                      </v-icon>
                    </v-btn>
                  </v-list-item-action>

                  <v-list-item-action v-if="item.asset && isTabularFile(item.path)">
                    <v-tooltip location="top">
                      <template #activator="{ props: tableProps }">
                        <v-btn
                          icon
                          variant="text"
                          v-bind="tableProps"
                          @click.stop.prevent="viewAsTable(item)"
                        >
                          <v-icon color="primary">
                            mdi-table
                          </v-icon>
                        </v-btn>
                      </template>
                      <span>View as table (you can also click on the item itself)</span>
                    </v-tooltip>
                  </v-list-item-action>

                  <v-list-item-action v-if="item.asset">
                    <v-tooltip location="top">
                      <template #activator="{ props: openInBtnProps }">
                        <v-btn
                          icon
                          variant="text"
                          :href="inlineURI(item.asset.asset_id)"
                          v-bind="openInBtnProps"
                        >
                          <v-icon color="primary">
                            mdi-open-in-app
                          </v-icon>
                        </v-btn>
                      </template>
                      <span v-if="isTabularFile(item.path)">Open asset in browser</span>
                      <span v-else>Open asset in browser (you can also click on the item itself)</span>
                    </v-tooltip>
                  </v-list-item-action>

                  <v-list-item-action v-if="item.asset">
                    <v-tooltip location="top">
                      <template #activator="{ props: downloadProps }">
                        <v-btn
                          icon
                          variant="text"
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
                          variant="text"
                          :href="assetMetadataURI(item.asset.asset_id)"
                          target="_blank"
                          rel="noreferrer"
                          v-bind="infoProps"
                          @click.stop
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
                          @click.stop.prevent
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
import axios from 'axios';

import { dandiRest, user } from '@/rest';
import { useDandisetStore } from '@/stores/dandiset';
import type { AssetPath } from '@/types';
import { getExternalServices } from '@/utils/externalServices';
import FileBrowserPagination from '@/components/FileBrowser/FileBrowserPagination.vue';
import FileUploadInstructions from '@/components/FileBrowser/FileUploadInstructions.vue';
import TableViewerDialog from '@/components/FileBrowser/TableViewerDialog.vue';
import { isTabularFile } from '@/utils/tabular';

const rootDirectory = '';
const FILES_PER_PAGE = 15;
// Query parameter holding the path of the asset open in the table viewer.
const TABLE_QUERY_PARAM = 'table';

function firstQueryValue(value: unknown): string | undefined {
  if (Array.isArray(value)) {
    return value[0] ?? undefined;
  }
  return typeof value === 'string' ? value : undefined;
}

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

const deletePopupOpen = ref(false);

// The tabular asset currently displayed in the table viewer
const itemToView: Ref<AssetPath | null> = ref(null);
const tableViewerOpen = ref(false);

const page = ref(1);
const pages = ref(0);
const updating = ref(false);

// Computed
const owners = computed(() => store.owners?.map((u) => u.username) || null);
const currentDandiset = computed(() => store.dandiset);
const unembargo_in_progress = computed(() => currentDandiset.value?.dandiset.embargo_status === 'UNEMBARGOING')
const splitLocation = computed(() => location.value.split('/'));
const isAdmin = computed(() => user.value?.admin || false);
const isOwner = computed(() => !!(
  user.value && owners.value?.includes(user.value?.username)
));
const itemsNotFound = computed(() => items.value && !items.value.length);
const parentLocation = computed(() => location.value.split('/').slice(0, -1).join('/'));



function locationSlice(index: number) {
  return `${splitLocation.value.slice(0, index + 1).join('/')}/`;
}

// The route for a directory, so that directory rows can be rendered as links.
function locationRoute(newLocation: string): RouteLocationRaw {
  return {
    name: 'fileBrowser',
    query: { location: newLocation, page: '1' },
  } as RouteLocationRaw;
}

// The open table is recorded in the URL, so that the link can be shared and
// comes back with the viewer already open. The route watcher does the opening.
function tableRoute(item: AssetPath): RouteLocationRaw {
  return {
    name: 'fileBrowser',
    query: { ...route.query, [TABLE_QUERY_PARAM]: item.path },
  } as RouteLocationRaw;
}

// Every row is a real link: directories and tabular assets are in-app routes,
// while other assets point straight at the asset itself.
function rowLink(item: AssetPath) {
  if (!item.asset) {
    return { to: locationRoute(item.path) };
  }
  if (isTabularFile(item.path)) {
    return { to: tableRoute(item) };
  }
  return { href: inlineURI(item.asset.asset_id) };
}

function viewAsTable(item: AssetPath) {
  router.push(tableRoute(item));
}

function closeTableViewer() {
  const query = { ...route.query };
  delete query[TABLE_QUERY_PARAM];
  router.replace({ name: 'fileBrowser', query } as RouteLocationRaw);
}

// Open (or close) the viewer to match the current URL.
function syncTableViewerWithRoute() {
  const target = firstQueryValue(route.query[TABLE_QUERY_PARAM]);
  const match = target
    ? items.value?.find(
      (item) => item.path === target && item.asset && isTabularFile(item.path),
    )
    : undefined;

  if (match) {
    itemToView.value = match;
    tableViewerOpen.value = true;
  } else {
    tableViewerOpen.value = false;
  }
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
  return filesize(item.aggregate_size, { round: 1, base: 10, standard: 'si' });
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
      syncTableViewerWithRoute();
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

  // The viewer can only be opened once the item it refers to has been loaded.
  syncTableViewerWithRoute();
}

function setItemToDelete(item: AssetPath) {
  itemToDelete.value = item;
  deletePopupOpen.value = true;
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
  deletePopupOpen.value = false;
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

// The listing last requested, so that query changes which don't affect it
// (opening or closing the table viewer) don't trigger a refetch.
let fetchedListing: string | null = null;

// go to the directory specified in the URL if it changes
watch(() => route.query, (newRouteQuery) => {
  location.value = firstQueryValue(newRouteQuery.location) || rootDirectory;

  const listing = `${location.value}?page=${Number(newRouteQuery.page) || page.value}`;
  if (listing !== fetchedListing) {
    fetchedListing = listing;
    // Retrieve with new location
    getItems();
  } else {
    syncTableViewerWithRoute();
  }
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
