<template>
  <div v-if="currentDandiset && currentDandiset.dandiset.embargo_status !== 'UNEMBARGOING'">
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
            >{{ itemToDelete.name }}</span>?
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
              color="error"
              @click="deleteAsset(itemToDelete)"
            >
              Yes
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>

      <v-row>
        <v-col :cols="12">
          <v-card>
            <v-card-title>
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
            <v-list>
              <v-list-item
                v-for="item in items"
                :key="item.name"
                color="primary"
                @click="selectPath(item)"
              >
                <v-icon
                  class="mr-2"
                  color="primary"
                >
                  <template v-if="item.folder">
                    mdi-folder
                  </template>
                  <template v-else>
                    mdi-file
                  </template>
                </v-icon>
                {{ item.name }}
                <v-spacer />

                <v-list-item-action>
                  <v-btn
                    v-if="showDelete(item)"
                    icon
                    @click="itemToDelete = item"
                  >
                    <v-icon color="error">
                      mdi-delete
                    </v-icon>
                  </v-btn>
                </v-list-item-action>

                <v-list-item-action v-if="item.asset_id">
                  <v-btn
                    icon
                    :href="downloadURI(item.asset_id)"
                  >
                    <v-icon color="primary">
                      mdi-download
                    </v-icon>
                  </v-btn>
                </v-list-item-action>

                <v-list-item-action v-if="item.asset_id">
                  <v-btn
                    icon
                    :href="assetMetadataURI(item.asset_id)"
                    target="_blank"
                    rel="noopener"
                  >
                    <v-icon color="primary">
                      mdi-information
                    </v-icon>
                  </v-btn>
                </v-list-item-action>

                <v-list-item-action v-if="item.asset_id">
                  <v-menu
                    bottom
                    left
                  >
                    <template #activator="{ on, attrs }">
                      <v-btn
                        v-if="item.services.length"
                        color="primary"
                        icon
                        v-bind="attrs"
                        v-on="on"
                      >
                        <v-icon>mdi-dots-vertical</v-icon>
                      </v-btn>
                      <v-btn
                        v-else
                        color="primary"
                        disabled
                        icon
                      >
                        <v-icon>mdi-dots-vertical</v-icon>
                      </v-btn>
                    </template>
                    <v-list dense>
                      <v-subheader
                        v-if="item.services.length"
                        class="font-weight-medium"
                      >
                        EXTERNAL SERVICES
                      </v-subheader>

                      <v-list-item
                        v-for="el in item.services"
                        :key="el.name"
                        :href="el.url"
                      >
                        <v-list-item-title class="font-weight-light">
                          {{ el.name }}
                        </v-list-item-title>
                      </v-list-item>
                    </v-list>
                  </v-menu>
                </v-list-item-action>

                <v-list-item-action
                  v-if="item.size"
                  class="justify-end"
                  :style="{width: '4.5em'}"
                >
                  {{ fileSize(item) }}
                </v-list-item-action>
              </v-list-item>
            </v-list>
          </v-card>
        </v-col>
      </v-row>
      <v-pagination
        v-model="page"
        :length="pages"
      />
    </v-container>
  </div>
</template>

<script lang="ts">
import {
  computed, defineComponent, onMounted, Ref, ref, watch,
} from '@vue/composition-api';
import { RawLocation } from 'vue-router';
import filesize from 'filesize';

import { dandiRest } from '@/rest';
import store from '@/store';
import { AssetFile, AssetFolder, AssetStats } from '@/types';

const parentDirectory = '..';
const rootDirectory = '';

const FILES_PER_PAGE = 15;

const sortByName = (a: AssetStats, b: AssetStats) => {
  if (a.name > b.name) {
    return 1;
  }
  if (b.name > a.name) {
    return -1;
  }
  return 0;
};

const EXTERNAL_SERVICES = [
  {
    name: 'Bioimagesuite/Viewer',
    regex: '.nii(.gz)?$',
    maxsize: 1e9,
    endpoint: 'https://bioimagesuiteweb.github.io/unstableapp/viewer.html?image=',
  },

  {
    name: 'MetaCell/NWBExplorer',
    regex: '.nwb$',
    maxsize: 1e9,
    endpoint: 'http://nwbexplorer.opensourcebrain.org/nwbfile=',
  },
];

export default defineComponent({
  name: 'FileBrowser',
  props: {
    identifier: {
      type: String,
      required: true,
    },
    version: {
      type: String,
      required: true,
    },
  },
  setup(props, ctx) {
    const location = ref(rootDirectory);
    const itemToDelete = ref(null);
    const page = ref(1);
    const pages = ref(0);
    const updating = ref(false);
    const items: Ref<AssetStats[]> = ref([]);

    // Computed
    const owners = computed(() => store.state.dandiset.owners?.map((u) => u.username) || null);
    const currentDandiset = computed(() => store.state.dandiset.dandiset);
    const splitLocation = computed(() => location.value.split('/'));
    const isAdmin = computed(() => dandiRest.user?.admin || false);
    const isOwner = computed(() => !!(
      dandiRest.user
      && owners.value?.includes(dandiRest.user?.username)
    ));

    function getExternalServices(asset_id: string, name: string, size: number) {
      const { identifier, version } = props;
      return EXTERNAL_SERVICES
        .filter((service) => new RegExp(service.regex).test(name) && size <= service.maxsize)
        .map((service) => ({
          name: service.name,
          url: `${service.endpoint}${dandiRest.assetDownloadURI(identifier, version, asset_id)}`,
        }));
    }

    function locationSlice(index: number) {
      return `${splitLocation.value.slice(0, index + 1).join('/')}/`;
    }

    function selectPath(item: AssetFolder) {
      const { name, folder } = item;

      if (!folder) { return; }
      if (name === parentDirectory) {
        const slicedLocation = location.value.split('/').slice(0, -2);
        location.value = slicedLocation.length ? `${slicedLocation.join('/')}/` : '';
      } else {
        location.value = `${location.value}${name}`;
      }
    }

    function downloadURI(asset_id: string) {
      return dandiRest.assetDownloadURI(props.identifier, props.version, asset_id);
    }

    function assetMetadataURI(asset_id: string) {
      return dandiRest.assetMetadataURI(props.identifier, props.version, asset_id);
    }

    function fileSize(item: AssetStats) {
      return filesize(item.size || 0, { round: 1, base: 10, standard: 'iec' });
    }

    function showDelete(item: AssetStats) {
      return props.version === 'draft' && !item.folder && (isAdmin.value || isOwner.value);
    }

    async function getItems() {
      updating.value = true;
      const { folders, files, count } = await dandiRest.assetPaths(
        props.identifier, props.version, location.value, page.value, FILES_PER_PAGE,
      );

      // Set num pages
      pages.value = Math.ceil(count / FILES_PER_PAGE);

      // Create items
      // Parent directory if necessary
      const newItems = location.value !== rootDirectory
        ? [{ name: parentDirectory, folder: true }]
        : [];

      // Add folders
      newItems.push(...Object.keys(folders).map(
        (key) => ({ ...folders[key], name: `${key}/`, folder: true }),
      ).sort(sortByName));

      // Add items
      newItems.push(...Object.keys(files).map(
        (key) => {
          const { asset_id, size } = files[key];
          const services = getExternalServices(asset_id, key, size || 0);
          return {
            ...files[key],
            name: key,
            folder: false,
            services,
          };
        },
      ).sort(sortByName));

      // Assign values
      items.value = newItems;
      updating.value = false;
    }

    async function deleteAsset(item: AssetFile) {
      const { asset_id } = item;
      if (asset_id !== undefined) {
        // Delete the asset on the server.
        await dandiRest.deleteAsset(props.identifier, props.version, asset_id);

        // Recompute the items to display in the browser.
        getItems();
      }
      itemToDelete.value = null;
    }

    // Refresh files/folders whenever URL changes
    watch(location, getItems, { immediate: true });

    // Update URL if location changes
    watch(location, () => {
      const { location: existingLocation } = ctx.root.$route.query;

      // Reset page to 1 when location changes
      page.value = 1;

      // Update route when location changes
      if (existingLocation === location.value) { return; }
      ctx.root.$router.push({
        ...ctx.root.$route,
        query: { location: location.value },
      } as RawLocation);
    });

    // If the API call returns no items, go back to the root (shouldn't normally happen)
    watch(items, () => {
      if (items.value && !items.value.length) {
        location.value = rootDirectory;
      }
    });

    // go to the directory specified in the URL if it changes
    watch(() => ctx.root.$route, (route) => {
      location.value = route.query.location.toString() || rootDirectory;
    }, { immediate: true });

    // Fetch dandiset if necessary
    onMounted(() => {
      if (!store.state.dandiset.dandiset) {
        store.dispatch.dandiset.initializeDandisets({
          identifier: props.identifier,
          version: props.version,
        });
      }
    });

    getItems();

    return {
      location,
      currentDandiset,
      splitLocation,
      itemToDelete,
      rootDirectory,
      items,
      pages,
      page,
      updating,
      locationSlice,
      selectPath,
      downloadURI,
      assetMetadataURI,
      fileSize,
      showDelete,
      deleteAsset,
    };
  },
});
</script>
