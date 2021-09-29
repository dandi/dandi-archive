<template>
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
  </v-container>
</template>

<script lang="ts">
import filesize from 'filesize';
import {
  defineComponent, computed, ref, watchEffect, Ref,
} from '@vue/composition-api';

import { dandiRest } from '@/rest';
import store from '@/store';
import { draftVersion } from '@/utils/constants';
import { AssetStats } from '@/types';

const parentDirectory = '..';
const rootDirectory = '';

const sortByName = (a: any, b: any) => {
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
  setup(props) {
    const location = ref(rootDirectory);
    const owners: Ref<string[]> = ref([]);
    const itemToDelete = ref(null);
    const updating = ref(false);

    const currentDandiset = computed(() => store.state.dandiset.dandiset);
    const splitLocation = computed(() => location.value.split('/'));

    const items: Ref<AssetStats[]|null> = ref(null);

    async function getAssets() {
      const { version, identifier } = props;

      const data = await dandiRest.assetPaths(identifier, version, location.value);
      owners.value = (await dandiRest.owners(identifier)).data
        .map((x) => x.username);

      items.value = [
        ...location.value !== rootDirectory ? [{ name: parentDirectory, folder: true }] : [],
        ...Object.keys(data.folders).map(
          (key) => ({ ...data.folders[key], name: `${key}/`, folder: true }),
        ).sort(sortByName),
        ...Object.keys(data.files).map(
          (key) => {
            const { asset_id, size } = data.files[key];
            return {
              ...data.files[key],
              name: key,
              folder: false,
              services: EXTERNAL_SERVICES
                .filter((service) => new RegExp(service.regex).test(key) && size <= service.maxsize)
                .map((service) => ({
                  name: service.name,
                  url: `${service.endpoint}${dandiRest.assetDownloadURI(identifier, version, asset_id)}`,
                })),
            };
          },
        ).sort(sortByName),
      ];
    }

    watchEffect(async () => {
      updating.value = true;
      await getAssets();
      updating.value = false;
    }, { flush: 'sync' });

    function downloadURI(asset_id: string): string {
      return dandiRest.assetDownloadURI(props.identifier, props.version, asset_id);
    }

    function selectPath(item: any) {
      const { name, folder } = item;

      if (!folder) { return; }
      if (name === parentDirectory) {
        const slicedLocation = location.value.split('/').slice(0, -2);
        location.value = slicedLocation.length ? `${slicedLocation.join('/')}/` : '';
      } else {
        location.value = `${location.value}${name}`;
      }
    }

    function locationSlice(index: number): string {
      return `${splitLocation.value.slice(0, index + 1).join('/')}/`;
    }

    function assetMetadataURI(asset_id: string): string {
      return dandiRest.assetMetadataURI(props.identifier, props.version, asset_id);
    }

    function fileSize(item: any): string {
      return filesize(item.size, { round: 1, base: 10, standard: 'iec' });
    }

    function showDelete(item: any): boolean {
      return props.version === draftVersion
      && !item.folder
      && !!(dandiRest.user?.admin || (
        dandiRest.user && owners.value.includes(dandiRest.user?.username)));
    }

    async function deleteAsset(item: any) {
      const { asset_id } = item;
      if (asset_id !== undefined) {
        // Delete the asset on the server.
        await dandiRest.deleteAsset(props.identifier, props.version, asset_id);
        updating.value = true;
        await getAssets();
        updating.value = false;
      }
      itemToDelete.value = null;
    }

    if (!currentDandiset.value) {
      store.dispatch.dandiset.fetchDandiset({
        identifier: props.identifier,
        version: props.version,
      });
    }

    return {
      deleteAsset,
      showDelete,
      fileSize,
      assetMetadataURI,
      locationSlice,
      selectPath,
      downloadURI,
      currentDandiset,
      itemToDelete,
      rootDirectory,
      splitLocation,
      updating,
      items,
    };
  },
});
</script>
