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
                params: { identifier },
              }"
            >
              <v-icon>mdi-jellyfish</v-icon>
            </v-btn>
            <v-divider
              vertical
              class="ml-2 mr-3"
            />
            {{ location }}
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
      location: rootDirectory,
      loading: false,
    };
  },
  computed: {
    ...mapState('dandiset', ['publishDandiset']),
  },
  asyncComputed: {
    items: {
      async get() {
        const { version, identifier, location } = this;

        this.loading = true;
        const { data } = await publishRest.get(`dandisets/${identifier}/versions/${version}/assets/paths/`, {
          params: {
            path_prefix: location,
          },
        });

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
