<template>
  <v-container>
    <v-row>
      <v-col sm="6">
        <v-form>
          <!-- <v-card>
            <json-editor
              ref="JsonEditor"
              :schema="schema"
              v-model="model"
              class="pa-2"
            />
          </v-card> -->
          <!-- <template v-for="(item, i) in fields">
            <v-textarea
              v-if="fieldType(item) === 'object'"
              :key="i"
              :label="item.title"
              v-model="meta[i]"
            />
            <v-list
              v-else-if="fieldType(item) === 'array'"
              :key="i"
            >
              <v-subheader>{{item.title}}</v-subheader>
            </v-list>
            <v-text-field
              v-else-if="fieldType(item) === 'number'"
              :key="i"
              :label="item.title"
              type="number"
              v-model.number="meta[i]"
            />
            <v-text-field
              v-else
              :key="i"
              :label="item.title"
              :type="fieldType(item)"
              v-model="meta[i]"
            />
          </template> -->
          <v-card class="pa-2">
            <meta-node :item="schema" :initial="meta" />
          </v-card>
        </v-form>
      </v-col>
      <v-col sm="6">
        <v-card>
          <v-card-title>Schema Adherent Data</v-card-title>
          <v-divider />
          <vue-json-pretty class="ma-2" :data="meta" highlightMouseoverNode />
          <v-card-actions>
            <v-btn icon color="primary" class="mr-2" @click="download">
              <v-icon>mdi-download</v-icon>
            </v-btn>
            <v-radio-group v-model="yamlOutput" row>
              <v-radio label="YAML" :value="true" />
              <v-radio label="JSON" :value="false" />
            </v-radio-group>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import VueJsonPretty from 'vue-json-pretty';
import jsYaml from 'js-yaml';
import MetaNode from '@/components/MetaNode.vue';

export default {
  props: ['schema', 'model'],
  components: {
    // JsonEditor,
    VueJsonPretty,
    MetaNode,
  },
  data() {
    return {
      yamlOutput: true,
      meta: this.model,
    };
  },
  computed: {
    yaml() {
      return jsYaml.dump(this.meta);
    },
  },
  methods: {
    fieldType(item) {
      if (item.type === 'number' || item.type === 'integer') {
        return 'number';
      }
      return item.type;
    },
    saveDandiMeta() {
      this.girderRest.put(`/folder/${this.id}/metadata`, { dandiset: this.meta }, { params: { allowNull: false } });
    },
    download() {},
  },
};
</script>

<style>

</style>
