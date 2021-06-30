<template>
  <v-container>
    <v-dialog
      v-model="dialogActive"
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
          >{{ dialogName }}</span>?
          <strong>This action cannot be undone.</strong>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn
            @click="dialogActive = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="error"
            @click="deleteAsset(dialogName)"
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

              <v-list-item-action v-if="itemData[item.name]">
                <v-btn
                  icon
                  :href="itemData[item.name].download"
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
      itemData: {},
      owners: [],
      dialogActive: false,
      dialogName: '',
    };
  },
  computed: {
    splitLocation() {
      return this.location.split('/');
    },

    me() {
      return publishRest.user ? publishRest.user.username : null;
    },

    isAdmin() {
      return this.me && publishRest.user.admin;
    },

    isOwner() {
      return this.me && this.owners.includes(this.me);
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

        // flatten the assetPaths object into an array:
        let mapped = [];

        if (data.files) {
          mapped = Object.keys(data.files).map(
            (name) => ({ name, folder: false, ...data.files[name] }),
          );
          // set download links and uuids (needed for deleting) for files
          mapped.forEach((item) => {
            this.$set(this.itemData, item.name, {
              download: item.download_url,
              uuid: item.asset_id,
            });
          });
        }

        if (data.folders) {
          mapped = mapped.concat(Object.keys(data.folders).map(
            (name) => ({ name: `${name}/`, folder: true, ...data.folders[name] }),
          ));
        }

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

      // Update route when location changes
      if (existingLocation === location) { return; }
      this.$router.push({
        ...this.$route,
        query: { location },
      });
    },
    items(items) {
      if (items && !items.length) {
        // If the API call returns no items, go back to the root (shouldn't normally happen)
        this.location = rootDirectory;
      }
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
        const slicedLocation = this.location.split('/').slice(0, -2);
        this.location = slicedLocation.length ? `${slicedLocation.join('/')}/` : '';
      } else {
        this.location = `${this.location}${name}`;
      }
    },

    showDelete(item) {
      return !item.folder && (this.isAdmin || this.isOwner);
    },

    openDialog(name) {
      this.dialogName = name;
      this.dialogActive = true;
    },

    async deleteAsset(name) {
      const uuid = this.itemData[name] && this.itemData[name].uuid;
      if (uuid !== undefined) {
        // Delete the asset on the server.
        await publishRest.deleteAsset(this.identifier, this.version, uuid);

        // Recompute the items to display in the browser.
        this.$asyncComputed.items.update();
      }
      this.dialogActive = false;
    },
  },
};
</script>
