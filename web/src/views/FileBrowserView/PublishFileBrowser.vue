<template>
  <v-container>
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
              {{ rootDirectory }}
            </router-link>

            <template v-for="(part, i) in splitLocation">
              <template v-if="part">
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
            v-if="loading"
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
const rootDirectory = '/';

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
      loading: false,
      itemDownloads: {},
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

        this.loading = true;
        const data = await publishRest.assetPaths(identifier, version, location);

        let mapped = data.map((x) => ({ name: x, folder: isFolder(x) }));
        if (location !== rootDirectory && mapped.length) {
          mapped = [
            { name: parentDirectory, folder: true },
            ...mapped,
          ];
        }

        this.loading = false;
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

      // Create the download link in itemDownloads for each item in items
      this.itemDownloads = {};
      const { identifier, version, location } = this;

      items.filter((x) => !x.folder).map(async (item) => {
        const relativePath = `${location}${item.name}`;
        const {
          results: [asset],
        } = await publishRest.assets(identifier, version, { params: { path: relativePath } });

        this.$set(this.itemDownloads, item.name, publishRest.assetDownloadURI(asset));
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
  },
};
</script>
