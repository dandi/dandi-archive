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

      <v-col>
        <v-card class="mb-2">
          <v-card-title>
            <v-tooltip top>
              <template v-slot:activator="{ on }">
                <v-icon
                  left
                  :color="allModelsValid ? 'success' : 'error'"
                  v-on="on"
                >
                  <template v-if="allModelsValid">
                    mdi-checkbox-marked-circle
                  </template>
                  <template v-else>
                    mdi-alert-circle
                  </template>
                </v-icon>
              </template>
              <template v-if="allModelsValid">
                All metadata for this dandiset is valid.
              </template>
              <template v-else>
                There are errors in the metadata for this Dandiset.
              </template>
            </v-tooltip>
            {{ basicModel.name }}
          </v-card-title>
          <v-card-actions class="pt-0">
            <v-tooltip bottom>
              <template v-slot:activator="{ on }">
                <v-btn
                  icon
                  color="secondary"
                  v-on="on"
                  @click="closeEditor"
                >
                  <v-icon>
                    mdi-arrow-left
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
            <v-spacer />
            <v-tooltip bottom>
              <template v-slot:activator="{ on }">
                <v-btn
                  icon
                  v-on="on"
                  @click="download"
                >
                  <v-icon>
                    mdi-download
                  </v-icon>
                </v-btn>
              </template>
              <span>Download Metadata</span>
            </v-tooltip>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
    <v-row>
      <v-subheader>Click a field below to edit it.</v-subheader>
    </v-row>
    <v-row class="px-2">
      <template v-for="propKey in Object.keys(complexSchema.properties)">
        <v-dialog
          v-if="renderField(complexSchema.properties[propKey])"
          :key="propKey"
        >
          <template v-slot:activator="{ on }">
            <v-btn
              outlined
              class="mx-2 my-2"
              :color="sectionButtonColor(propKey)"
              v-on="on"
            >
              {{ complexSchema.properties[propKey].title || propKey }}
            </v-btn>
          </template>
          <v-card class="pa-2 px-4">
            <v-form
              :ref="`${propKey}-form`"
              v-model="complexModelValidation[propKey]"
            >
              <v-jsf
                :value="complexModel[propKey]"
                :schema="complexSchema.properties[propKey]"
                :options="CommonVJSFOptions"
                @input="setComplexModelProp(propKey, $event)"
              />
            </v-form>
          </v-card>
        </v-dialog>
      </template>
    </v-row>
    <v-divider class="my-5" />
    <v-row class="px-2">
      <v-form
        ref="basic-form"
        v-model="basicModelValid"
      >
        <v-jsf
          v-model="basicModel"
          :schema="basicSchema"
          :options="{...CommonVJSFOptions, hideReadOnly: true}"
        />
      </v-form>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import type { JSONSchema7 } from 'json-schema';

import {
  defineComponent, PropType, ref, computed,
} from '@vue/composition-api';

import jsYaml from 'js-yaml';

import VJsf from '@koumoul/vjsf/lib/VJsf';
import '@koumoul/vjsf/lib/deps/third-party';
import '@koumoul/vjsf/lib/VJsf.css';

import { publishRest } from '@/rest';
import { girderize } from '@/rest/publish';
import { DandiModel, isJSONSchema } from '@/utils/schema/types';
import { EditorInterface } from '@/utils/schema/editor';

function renderField(fieldSchema: JSONSchema7) {
  const { properties } = fieldSchema;

  if (fieldSchema.readOnly) { return false; }
  const allSubPropsReadOnly = properties !== undefined && Object.keys(properties).every(
    (key) => {
      const subProp = properties[key];
      return isJSONSchema(subProp) && subProp.readOnly;
    },
  );

  if (allSubPropsReadOnly) { return false; }
  return true;
}

const CommonVJSFOptions = {
  initialValidation: 'all',
};

export default defineComponent({
  name: 'Meditor',
  components: { VJsf },
  props: {
    schema: {
      type: Object as PropType<JSONSchema7>,
      required: true,
    },
    model: {
      type: Object as PropType<DandiModel>,
      required: true,
    },
  },
  setup(props, ctx) {
    // TODO: Replace once direct-vuex is added
    const store = ctx.root.$store;

    const { model: modelProp, schema: schemaProp } = props;
    const invalidPermissionSnackbar = ref(false);

    const editorInterface = new EditorInterface(schemaProp, modelProp);
    const {
      modelValid,
      basicSchema,
      basicModel,
      basicModelValid,
      complexSchema,
      complexModel,
      setComplexModelProp,
      complexModelValid,
      complexModelValidation,
    } = editorInterface;

    const closeEditor = () => { ctx.emit('close'); };

    function sectionButtonColor(propKey: string) {
      const sectionValid = complexModelValidation[propKey];
      if (sectionValid !== undefined && !sectionValid) {
        return 'error';
      }

      return undefined;
    }

    const publishDandiset = computed(() => store.state.dandiset.publishDandiset);
    const id = computed(() => publishDandiset.value?.meta.dandiset.identifier || null);
    function setDandiset(payload: any) {
      // TODO: Replace once direct-vuex is added
      store.commit('dandiset/setPublishDandiset', girderize(payload));
    }

    async function save() {
      const dandiset = editorInterface.getModel();

      try {
        const { status, data } = await publishRest.saveDandiset(
          id.value, publishDandiset.value.version, dandiset,
        );

        if (status === 200) {
          setDandiset(data);
          closeEditor();
        }
      } catch (error) {
        if (error.response.status === 403) {
          invalidPermissionSnackbar.value = true;
        }

        throw error;
      }
    }

    // TODO: Add back UI to toggle YAML vs JSON
    const yamlOutput = ref(false);
    const contentType = computed(() => (yamlOutput.value ? 'text/yaml' : 'application/json'));
    const output = computed(() => {
      const model = editorInterface.getModel();
      return yamlOutput.value ? jsYaml.dump(model) : JSON.stringify(model, null, 2);
    });

    function download() {
      const blob = new Blob([output.value], { type: contentType.value });

      const extension = contentType.value.split('/')[1];
      const filename = `dandiset.${extension}`;
      const link = document.createElement('a');

      link.href = URL.createObjectURL(blob);
      link.download = filename;
      link.click();
      URL.revokeObjectURL(link.href);
    }

    return {
      allModelsValid: modelValid,

      basicSchema,
      basicModel,
      basicModelValid,

      complexSchema,
      complexModel,
      complexModelValid,
      complexModelValidation,

      invalidPermissionSnackbar,
      renderField,
      closeEditor,
      save,
      download,
      sectionButtonColor,

      CommonVJSFOptions,

      setComplexModelProp,
    };
  },
});
</script>
