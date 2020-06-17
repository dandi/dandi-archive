<template>
  <v-container>
    <v-row>
      <v-col :cols="12">
        <v-data-table
          :items="items"
          :headers="headers"
          hide-default-header
          item-key="name"
          selectable-key="folder"
          @click:row="selectPath"
        >
          <template v-slot:header>
            {{ location }}
          </template>

        <!-- <template v-slot:item="{ item }">
          <v-row>
            <v-icon>mdi-folder</v-icon>
            <span>{{ item.name }}</span>
          </v-row>
        </template> -->
        </v-data-table>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { mapState } from 'vuex';
import { publishRest } from '@/rest';

const isFolder = (pathName) => (pathName.slice(-1) === '/');
const parentDirectory = '..';

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
      location: '/',
      // items: [],
      headers: [
        {
          text: 'Name',
          value: 'name',
          align: 'start',
        },
      ],
    };
  },
  computed: {
    ...mapState('dandiset', ['publishDandiset']),
  },
  asyncComputed: {
    items: {
      async get() {
        const { version, identifier, location } = this;
        const { data } = await publishRest.get(`dandisets/${identifier}/versions/${version}/assets/paths/`, {
          params: {
            path_prefix: location,
          },
        });

        const mapped = data.map((x) => ({ name: x, folder: isFolder(x) }));
        return [
          { name: parentDirectory, folder: true },
          ...mapped,
        ];
      },
      default: [],
    },
  },
  watch: {},
  created() {},
  methods: {
    selectPath({ name }) {
      if (name === parentDirectory) {
        this.location = `${this.location.split('/').slice(0, -2).join('/')}/`;
      } else {
        this.location = `${this.location}${name}`;
      }
    },
  },
};
</script>
