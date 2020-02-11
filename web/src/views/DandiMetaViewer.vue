<template>
  <div>
    <h1>DANDI Metadata</h1>
    <v-container>
      <v-row>
        <v-col sm="6">
          <v-card>
            <json-editor
              ref="JsonEditor"
              :schema="schema"
              v-model="model"
              class="pa-2"
              @input="test"
            />
          </v-card>
        </v-col>
        <v-col sm="6">
          <v-card>
            <v-card-title>Schema Adherent Data</v-card-title>
            <v-divider />
            <vue-json-pretty class="ma-2" :data="model" highlightMouseoverNode />
            <v-card-actions>
              <v-switch label="Yaml" v-model="yamlOutput"/>
              <v-btn icon color="primary">
                <v-icon>mdi-download</v-icon>
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>
<script>
import { mapState } from 'vuex';
import { debounce } from 'lodash';
import JsonEditor from 'vue-json-ui-editor';
import VueJsonPretty from 'vue-json-pretty';
import jsYaml from 'js-yaml';
import {
  VForm,
  VTextField,
  VTextarea,
  VSelect,
  VInput,
  VRadio,
  VCheckbox,
  VRating,
  VSwitch,
} from 'vuetify/lib';

// import SCHEMA from '@/assets/subscription_schema.json';
import SCHEMA from '@/assets/json_schema.json';

const commonProps = { solo: true };

JsonEditor.setComponent('form', VForm);
JsonEditor.setComponent('text', VTextField, commonProps);
JsonEditor.setComponent('textarea', VTextarea, commonProps);
JsonEditor.setComponent('select', VSelect, commonProps);
JsonEditor.setComponent('number', VTextField, { ...commonProps, number: true });
JsonEditor.setComponent('input', VInput, commonProps);
JsonEditor.setComponent('radio', VRadio);
JsonEditor.setComponent('checkbox', VCheckbox);
JsonEditor.setComponent('rate', VRating);
JsonEditor.setComponent('email', VInput, commonProps);
JsonEditor.setComponent('url', VInput, commonProps);
JsonEditor.setComponent('switch', VSwitch);

export default {
  props: ['id'],
  components: {
    JsonEditor,
    VueJsonPretty,
  },
  data() {
    return {
      valid: false,
      schema: SCHEMA,
      yamlOutput: false,
      meta: {},
      errors: {},
      model: {},
    };
  },
  computed: {
    yaml() {
      return jsYaml.dump(this.model);
    },
    ...mapState({
      selected: state => (state.selected.length === 1 ? state.selected[0] : undefined),
      girderRest: 'girderRest',
    }),
  },
  watch: {
    selected(val) {
      if (!val || !val.meta || !val.meta.dandiset) {
        this.meta = {};
      } else {
        this.meta = { ...val.meta.dandiset };
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
