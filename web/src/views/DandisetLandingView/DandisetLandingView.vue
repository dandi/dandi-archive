<template>
  <div>
    <meta-editor
      v-if="edit && Object.entries(meta).length"
      :schema="schema"
      :model="meta"
      :create="create"
      @close="edit = false"
    />
    <template v-else>
      <v-container>
        <v-row>
          <v-col
            class="xs"
            lg="9"
            xl="6"
          >
            <v-card>
              <v-card-title>
                {{ meta.name }}
                <v-chip
                  v-if="meta.version"
                  class="primary ml-2"
                  round
                >
                  Version: {{ meta.version }}
                </v-chip>
                <v-chip
                  v-if="!published"
                  class="orange ml-2"
                  round
                >
                  This dataset has not been published!
                </v-chip>
              </v-card-title>
              <v-list
                v-if="meta.identifier"
                dense
                class="py-0"
              >
                <v-list-item>
                  <v-list-item-content>
                    Identifier: {{ meta.identifier }}
                  </v-list-item-content>
                </v-list-item>
                <v-list-item>
                  <v-list-item-content>
                    <a :href="permalink">
                      {{ permalink }}
                    </a>
                  </v-list-item-content>
                </v-list-item>
              </v-list>
              <v-card-actions
                v-if="selected"
                class="py-0"
              >
                <v-btn
                  icon
                  :to="`/collection/${selected.parentId}`"
                >
                  <v-icon>mdi-arrow-left</v-icon>
                </v-btn>
                <v-tooltip
                  right
                  :disabled="loggedIn"
                >
                  <template v-slot:activator="{ on }">
                    <div v-on="on">
                      <v-btn
                        icon
                        :disabled="!loggedIn"
                        @click="edit = true"
                      >
                        <v-icon>mdi-pencil</v-icon>
                      </v-btn>
                    </div>
                  </template>
                  You must be logged in to edit.
                </v-tooltip>
                <v-btn
                  :to="`/folder/${id}`"
                  icon
                >
                  <v-icon>mdi-file-tree</v-icon>
                </v-btn>
              </v-card-actions>
              <v-list dense>
                <v-divider />
                <v-list-item>
                  <v-list-item-content>
                    Uploaded by {{ uploader }}
                  </v-list-item-content>
                </v-list-item>
                <v-list-item>
                  <v-list-item-content>
                    Last modified {{ last_modified }}
                  </v-list-item-content>
                </v-list-item>
                <v-list-item v-if="details">
                  <v-list-item-content>
                    Files: {{ details.nItems }}, Folders: {{ details.nFolders }}
                  </v-list-item-content>
                </v-list-item>
                <v-divider />
                <template v-if="meta.description">
                  <v-subheader>Description</v-subheader>
                  <v-list-item>
                    <v-list-item-content>
                      {{ meta.description }}
                    </v-list-item-content>
                  </v-list-item>
                </template>
                <template v-if="meta.contributors">
                  <v-subheader>Contributors</v-subheader>
                  <v-list-item
                    v-for="(item, i) in meta.contributors"
                    :key="i"
                  >
                    <v-list-item-content>{{ item }}</v-list-item-content>
                  </v-list-item>
                </template>
                <template v-for="(item, k) in extraFields">
                  <v-subheader :key="k">
                    {{ k }}
                  </v-subheader>
                  <v-list-item :key="k">
                    <v-list-item-content>
                      <template v-if="['object', 'array'].includes(schema.properties[k].type)">
                        <vue-json-pretty
                          :data="item"
                          highlight-mouseover-node
                        />
                      </template>
                      <template v-else>
                        {{ item }}
                      </template>
                    </v-list-item-content>
                  </v-list-item>
                </template>
              </v-list>
            </v-card>
          </v-col>
        </v-row>
      </v-container>
    </template>
  </div>
</template>

<script>
import filesize from 'filesize';
import { mapState } from 'vuex';
import VueJsonPretty from 'vue-json-pretty';

import MetaEditor from '@/components/MetaEditor.vue';
import { dandiUrl } from '@/utils';
import girderRest, { loggedIn } from '@/rest';

import SCHEMA from '@/assets/schema/base.json';
import NEW_SCHEMA from '@/assets/schema/new_dandiset.json';
import NWB_SCHEMA from '@/assets/schema/nwb.json';

export default {
  name: 'DandisetLandingView',
  components: {
    MetaEditor,
    VueJsonPretty,
  },
  props: {
    id: {
      type: String,
      required: true,
    },
    create: {
      type: Boolean,
      required: false,
      default: () => false,
    },
  },
  data() {
    return {
      dandiUrl,
      meta: {},
      edit: false,
      published: false,
      uploader: '',
      last_modified: null,
      details: null,
      mainFields: [
        'name',
        'version',
        'contributors',
        'description',
        'identifier',
      ],
    };
  },
  computed: {
    loggedIn,
    schema() {
      if (this.create) {
        return NEW_SCHEMA;
      }

      if (this.edit) {
        return SCHEMA;
      }

      const properties = { ...SCHEMA.properties, ...NWB_SCHEMA.properties };
      const required = [...SCHEMA.required, ...NWB_SCHEMA.required];

      return { properties, required };
    },
    permalink() {
      return `${this.dandiUrl}/dandiset/${this.meta.identifier}/draft`;
    },
    extraFields() {
      const { meta, mainFields } = this;
      const extra = Object.keys(meta).filter(
        (x) => !mainFields.includes(x) && x in this.schema.properties,
      );
      return extra.reduce((obj, key) => ({ ...obj, [key]: meta[key] }), {});
    },
    computedSize() {
      if (!this.selected || !this.selected.size) return null;
      return filesize(this.selected.size);
    },
    ...mapState('girder', {
      selected: (state) => (state.selected.length === 1 ? state.selected[0] : undefined),
    }),
  },
  watch: {
    async selected(val) {
      if (!val || !val.meta || !val.meta.dandiset) {
        this.meta = {};
        return;
      }

      this.meta = { ...val.meta.dandiset };
      this.last_modified = new Date(val.updated).toString();

      let res = await girderRest.get(`/user/${val.creatorId}`);
      if (res.status === 200) {
        const { data: { firstName, lastName } } = res;
        this.uploader = `${firstName} ${lastName}`;
      }

      res = await girderRest.get(`/folder/${val._id}/details`);
      if (res.status === 200) {
        this.details = res.data;
      }
    },
    id: {
      immediate: true,
      async handler(value) {
        if (!this.selected || !this.meta.length) {
          const resp = await girderRest.get(`folder/${value}`);
          this.$store.commit('girder/setSelected', [resp.data]);
        }
      },
    },
  },
};
</script>
