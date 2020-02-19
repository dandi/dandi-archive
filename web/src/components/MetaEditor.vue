<template>
  <v-container>
    <v-row>
      <v-col sm="6">
        <v-form>
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
