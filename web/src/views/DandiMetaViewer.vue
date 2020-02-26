<template>
  <div>
    <meta-editor
      v-if="edit && Object.entries(meta).length"
      @close="edit = false"
      :schema="schema"
      :model="meta"
    />
    <template v-else>
      <v-container>
        <v-row>
          <v-col sm="6">
            <v-card>
              <v-card-title>
                {{meta.name}}
                <v-chip
                  v-if="meta.version"
                  class="primary ml-2"
                  round
                >
                  Version: {{meta.version}}
                </v-chip>
                <v-chip
                  v-if="!published"
                  class="orange ml-2"
                  round
                >
                  This dataset has not been published!
                </v-chip>
              </v-card-title>
              <v-card-actions>
                <v-btn
                  icon
                  @click="$router.push(`/collection/${selected.parentId}`)"
                >
                  <v-icon>mdi-arrow-left</v-icon>
                </v-btn>
                <v-btn
                  @click="edit = true"
                  icon
                >
                  <v-icon>mdi-pencil</v-icon>
                </v-btn>
              </v-card-actions>
              <v-divider />
              <v-list dense>
                <v-list-item>
                  <v-list-item-content>
                    Uploaded by {{uploader}}
                  </v-list-item-content>
                </v-list-item>
                <v-list-item>
                  <v-list-item-content>
                    Last modified {{last_modified}}
                  </v-list-item-content>
                </v-list-item>
                <v-list-item v-if="details">
                  <v-list-item-content>
                    <!-- Size: {{computedSize}}, Files: {{details.nItems}}, Folders: {{details.nFolders}} -->
                    Files: {{details.nItems}}, Folders: {{details.nFolders}}
                  </v-list-item-content>
                </v-list-item>
                <v-divider />
                <template v-if="meta.description">
                  <v-subheader>Description</v-subheader>
                  <v-list-item>
                    <v-list-item-content>
                      {{meta.description}}
                    </v-list-item-content>
                  </v-list-item>
                </template>
                <template v-if="meta.contributors">
                  <v-subheader>Contributors</v-subheader>
                  <v-list-item v-for="(item, i) in meta.contributors" :key="i">
                    <v-list-item-content>{{item}}</v-list-item-content>
                  </v-list-item>
                </template>
              </v-list>
            </v-card>
          </v-col>
          <v-col sm="6">
            <v-card>
              <v-expansion-panels multiple>
                <v-expansion-panel v-for="(field, k) in extraFields" :key="k">
                  <v-expansion-panel-header>
                    {{schema.properties[k].title || k}}
                  </v-expansion-panel-header>
                  <v-expansion-panel-content>
                    <template v-if="['object', 'array'].includes(schema.properties[k].type)">
                      <vue-json-pretty :data="field" highlightMouseoverNode />
                    </template>
                    <template v-else>{{field}}</template>
                  </v-expansion-panel-content>
                </v-expansion-panel>
              </v-expansion-panels>
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
import { debounce } from 'lodash';
import VueJsonPretty from 'vue-json-pretty';

import MetaEditor from '@/components/MetaEditor.vue';
import SCHEMA from '@/assets/schema/base.json';

export default {
  name: 'DandisetLandingPage',
  props: ['id'],
  components: {
    MetaEditor,
    VueJsonPretty,
  },
  data() {
    return {
      valid: false,
      schema: SCHEMA,
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
      ],
    };
  },
  computed: {
    extraFields() {
      const { meta, mainFields } = this;
      const extra = Object.keys(meta).filter(x => !mainFields.includes(x));
      return extra.reduce((obj, key) => ({ ...obj, [key]: meta[key] }), {});
    },
    computedSize() {
      if (!this.selected || !this.selected.size) return null;
      return filesize(this.selected.size);
    },
    ...mapState({
      selected: state => (state.selected.length === 1 ? state.selected[0] : undefined),
      girderRest: 'girderRest',
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

      let res = await this.girderRest.get(`/user/${val.creatorId}`);
      if (res.status === 200) {
        const { data: { firstName, lastName } } = res;
        this.uploader = `${firstName} ${lastName}`;
      }

      res = await this.girderRest.get(`/folder/${val._id}/details`);
      if (res.status === 200) {
        this.details = res.data;
      }
    },
    valid: debounce(function debouncedValid(valid) {
      if (valid) {
        this.saveDandiMeta();
      }
    }, 1000),
  },
  methods: {
    saveDandiMeta() {
      this.girderRest.put(`/folder/${this.id}/metadata`, { dandiset: this.meta }, { params: { allowNull: false } });
    },
    setMetaObject(val, index) {
      try {
        this.$set(this.meta, index, JSON.parse(val));
        this.$delete(this.errors, index);
      } catch (err) {
        this.$set(this.errors, index, err.message);
      }
    },
  },
  async created() {
    if (!this.selected || !this.meta.length) {
      const resp = await this.girderRest.get(`folder/${this.id}`);
      this.$store.commit('setSelected', [resp.data]);
    }
  },
};
</script>

<style>
</style>
