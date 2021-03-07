<template>
  <v-container>
    <v-row>
      <v-snackbar
        v-model="invalidPermissionSnackbar"
        top
        :timeout="2000"
        color="error"
      >
        Save Failed: Insufficient Permissions
        <v-btn
          icon
          @click="invalidPermissionSnackbar = false"
        >
          <v-icon color="white">
            mdi-close-circle
          </v-icon>
        </v-btn>
      </v-snackbar>

      <v-col sm="6">
        <v-card class="mb-2">
          <v-card-title>{{ meta.name }}</v-card-title>
          <v-card-text class="pb-0">
            <template v-if="!errors || !errors.length">
              <v-alert
                dense
                type="success"
              >
                No errors
              </v-alert>
            </template>
            <template v-else>
              <v-alert
                v-for="error in errors"
                :key="error.schemaPath"
                dense
                type="error"
                text-color="white"
              >
                {{ errorMessage(error) }}
              </v-alert>
            </template>
          </v-card-text>
          <v-card-actions class="pt-0">
            <v-tooltip bottom>
              <template v-slot:activator="{ on }">
                <v-btn
                  icon
                  color="error"
                  v-on="on"
                  @click="closeEditor"
                >
                  <v-icon>
                    mdi-close-circle
                  </v-icon>
                </v-btn>
              </template>
              <span>Cancel</span>
            </v-tooltip>
            <v-tooltip bottom>
              <template v-slot:activator="{ on }">
                <v-btn
                  icon
                  color="primary"
                  v-on="on"
                  @click="save"
                >
                  <v-icon>
                    mdi-content-save
                  </v-icon>
                </v-btn>
              </template>
              <span>Save</span>
            </v-tooltip>
          </v-card-actions>
        </v-card>
        <v-form>
          <v-card class="pa-2">
            <meta-node
              v-model="meta"
              class="pt-3"
              :schema="schema"
              :initial="meta"
            />
          </v-card>
        </v-form>
      </v-col>
      <v-col sm="6">
        <v-card>
          <v-card-title>Dandiset Metadata</v-card-title>
          <v-divider />
          <v-card-actions class="py-0">
            <v-btn
              icon
              color="primary"
              class="mr-2"
              @click="download"
            >
              <v-icon>mdi-download</v-icon>
            </v-btn>
            <v-radio-group
              v-model="yamlOutput"
              row
            >
              <v-radio
                label="YAML"
                :value="true"
              />
              <v-radio
                label="JSON"
                :value="false"
              />
            </v-radio-group>
          </v-card-actions>
          <vue-json-pretty
            class="ma-2"
            :data="meta"
            highlight-mouseover-node
          />
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { mapState, mapMutations } from 'vuex';
import VueJsonPretty from 'vue-json-pretty';
import jsYaml from 'js-yaml';
import Ajv from 'ajv';

import { girderRest } from '@/rest';

import MetaNode from './MetaNode.vue';

const ajv = new Ajv({ allErrors: true });

export default {
  components: {
    VueJsonPretty,
    MetaNode,
  },
  props: {
    schema: {
      type: Object,
      required: true,
    },
    model: {
      type: Object,
      required: true,
    },
  },
  data() {
    return {
      yamlOutput: true,
      errors: [],
      meta: this.copyValue(this.model),
      invalidPermissionSnackbar: false,
    };
  },
  computed: {
    validate() {
      return ajv.compile(this.schema);
    },
    contentType() {
      return this.yamlOutput ? 'text/yaml' : 'application/json';
    },
    output() {
      return this.yamlOutput ? jsYaml.dump(this.meta) : JSON.stringify(this.meta, null, 2);
    },
    ...mapState('dandiset', {
      id: (state) => (state.girderDandiset ? state.girderDandiset._id : null),
    }),
  },
  watch: {
    meta: {
      handler(val) {
        this.validate(val);
        this.errors = this.validate.errors;
      },
      deep: true,
    },
  },
  created() {
    this.validate(this.meta);
    this.errors = this.validate.errors;
  },
  methods: {
    closeEditor() {
      this.$emit('close');
    },
    async save() {
      try {
        const { status, data } = await girderRest.put(`folder/${this.id}/metadata`, { dandiset: this.meta });
        if (status === 200) {
          this.setGirderDandiset(data);
          this.closeEditor();
        }
      } catch (error) {
        if (error.response.status === 403) {
          this.invalidPermissionSnackbar = true;
        }

        throw error;
      }
    },
    publish() {
      // Call this.save()
      // Probably call publish endpoint on the backend
    },
    errorMessage(error) {
      const path = error.dataPath.substring(1);
      let message = `${path} ${error.message}`;

      if (error.keyword === 'const') {
        message += `: ${error.params.allowedValue}`;
      }

      return message;
    },
    copyValue(val) {
      if (val instanceof Object && !Array.isArray(val)) {
        return { ...val };
      }
      return val.valueOf();
    },
    download() {
      const blob = new Blob([this.output], { type: this.contentType });

      const extension = this.contentType.split('/')[1];
      const filename = `dandiset.${extension}`;
      const link = document.createElement('a');

      link.href = URL.createObjectURL(blob);
      link.download = filename;
      link.click();
      URL.revokeObjectURL(link.href);
    },
    ...mapMutations('dandiset', ['setGirderDandiset']),
  },
};
</script>
