<template>
  <v-container>
    <v-row>
      <v-col sm="6">
        <v-card class="my-2">
          <v-card-title>
            {{model.name}}
            <v-spacer />
            <v-btn @click="save" icon color="primary">
              <v-icon>
                mdi-content-save
              </v-icon>
            </v-btn>
            <v-btn @click="closeEditor" icon color="error">
              <v-icon>
                mdi-close-circle
              </v-icon>
            </v-btn>
          </v-card-title>
          <!-- <v-card-actions>
            <v-chip></v-chip>
          </v-card-actions> -->
        </v-card>
        <v-form>
          <v-card class="pa-2">
            <meta-node class="pt-3" :schema="schema" :initial="meta" v-model="meta"/>
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
    VueJsonPretty,
    MetaNode,
  },
  data() {
    return {
      yamlOutput: true,
      meta: this.copyValue(this.model),
    };
  },
  computed: {
    contentType() {
      return this.yamlOutput ? 'text/yaml' : 'application/json';
    },
    output() {
      return this.yamlOutput ? jsYaml.dump(this.meta) : JSON.stringify(this.meta, null, 2);
    },
  },
  methods: {
    closeEditor() {
      this.$emit('close');
    },
    save() {
      // Make rest requests
      this.closeEditor();
    },
    copyValue(val) {
      if (val instanceof Object && !Array.isArray(val)) {
        return { ...val };
      }
      return val.valueOf();
    },
    fieldType(item) {
      if (item.type === 'number' || item.type === 'integer') {
        return 'number';
      }
      return item.type;
    },
    saveDandiMeta() {
      this.girderRest.put(`/folder/${this.id}/metadata`, { dandiset: this.meta }, { params: { allowNull: false } });
    },
    download() {
      const blob = new Blob([this.output], { type: this.contentType });

      const extension = this.contentType.split('/')[1];
      const filename = `dandidata.${extension}`;
      const link = document.createElement('a');

      link.href = URL.createObjectURL(blob);
      link.download = filename;
      link.click();
      URL.revokeObjectURL(link.href);
    },
  },
};
</script>

<style>

</style>
