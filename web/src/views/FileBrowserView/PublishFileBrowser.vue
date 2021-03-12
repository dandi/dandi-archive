<template>
  <v-container>
    <v-dialog
      v-model="dialog.active"
      persistent
      max-width="60vh"
    >
      <v-card>
        <v-card-title class="headline">
          Really delete this asset?
        </v-card-title>

        <v-card-text>
          Are you sure you want to delete asset <span
          class="font-italic">{{dialog.name}}</span>?
            <strong>This action cannot be undone.</strong>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn
            @click="dialog.active = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="error"
            @click="deleteAsset(dialog.name)"
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
              <v-icon>mdi-jellyfish</v-icon>
            </v-btn>
            <v-divider
              vertical
              class="ml-2 mr-3"
            />
            <router-link
              :to="{ name: 'fileBrowser', query: { location: rootDirectory } }"
              style="text-decoration: none;"
            >
              <v-icon>mdi-home</v-icon>
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
                {{ i === splitLocation.length - 1 ? '' : '/' }}
              </template>
            </template>
          </v-card-title>
          <v-progress-linear
            v-if="$asyncComputed.items.updating"
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
                  @click="openDialog(item.name)"
                >
                  <v-icon color="error">
                    mdi-delete
                  </v-icon>
                </v-btn>
              </v-list-item-action>

              <v-list-item-action v-if="itemDownloads[item.name]">
                <v-btn
                  icon
                  :href="itemDownloads[item.name]"
                >
                  <v-icon color="primary">
                    mdi-download
                  </v-icon>
                </v-btn>
              </v-list-item-action>
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { mapState } from 'vuex';
import { publishRest } from '@/rest';

const isFolder = (pathName) => (pathName.slice(-1) === '/');
const parentDirectory = '..';
const rootDirectory = '';

export default {
  name: 'PublishFileBrowser',
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
  data() {
    return {
      rootDirectory,
      location: rootDirectory,
      itemDownloads: {},
      itemDeletes: {},
      owners: [],
      dialog: {
        active: false,
        name: '',
      },
    };
  },
  computed: {
    splitLocation() {
      return this.location.split('/');
    },
    ...mapState('dandiset', ['publishDandiset']),
  },
  asyncComputed: {
    items: {
      async get() {
        const { version, identifier, location } = this;

        const data = await publishRest.assetPaths(identifier, version, location);
        this.owners = (await publishRest.owners(identifier)).data
          .map((x) => x.username);

        let mapped = data.map((x) => ({ name: x, folder: isFolder(x) }));
        if (location !== rootDirectory && mapped.length) {
          mapped = [
            { name: parentDirectory, folder: true },
            ...mapped,
          ];
        }

        return mapped;
      },
      default: null,
    },
  },
  watch: {
    location(location) {
      const { location: existingLocation } = this.$route.query;

      if (existingLocation && existingLocation === location) { return; }
      this.$router.push({
        ...this.$route,
        query: { location },
      });
    },
    items(items) {
      if (items && !items.length) {
        // If the API call returns no items, go back to the root (shouldn't normally happen)
        this.location = rootDirectory;
        return;
      }

      // Create download and delete links in local data for each item in items
      this.itemDownloads = {};
      this.itemDeletes = {};
      const { identifier, version, location } = this;

      items.filter((x) => !x.folder).map(async (item) => {
        const relativePath = `${location}${item.name}`;
        const {
          results: [asset],
        } = await publishRest.assets(identifier, version, { params: { path: relativePath } });

        this.$set(
          this.itemDownloads,
          item.name,
          publishRest.assetDownloadURI(identifier, version, asset),
        );

        this.$set(this.itemDeletes, item.name, {
          identifier,
          version,
          uuid: asset.uuid,
        });
      });
    },
    $route: {
      immediate: true,
      handler(route) {
        this.location = route.query.location || rootDirectory;
      },
    },
  },
  methods: {
    locationSlice(index) {
      return `${this.splitLocation.slice(0, index + 1).join('/')}/`;
    },
    selectPath(item) {
      const { name, folder } = item;

      if (!folder) { return; }
      if (name === parentDirectory) {
        this.location = `${this.location.split('/').slice(0, -2).join('/')}/`;
      } else {
        this.location = `${this.location}${name}`;
      }
    },

    showDelete(item) {
      const me = publishRest.user ? publishRest.user.username : null;

      const isAdmin = me && publishRest.user.admin;
      const isOwner = me && this.owners.includes(me);

      return !item.folder && (isAdmin || isOwner);
    },

    openDialog(name) {
      this.dialog.name = name;
      this.dialog.active = true;
    },

    async deleteAsset(name) {
      const asset = this.itemDeletes[name];
      if (asset !== undefined) {
        // Delete the asset on the server.
        const { identifier, version, uuid } = asset;
        await publishRest.deleteAsset(identifier, version, uuid);

        // Recompute the items to display in the browser.
        this.$asyncComputed.items.update();
      }
      this.dialog.active = false;
    },
  },
};
</script>
