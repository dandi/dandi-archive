<template>
  <v-card
    v-if="schema"
    v-page-title="model.name"
    class="overflow-hidden"
  >
    <v-row>
      <v-col>
        <v-card
          rounded="0"
          flat
        >
          <v-card-actions class="pt-0">
            <v-tooltip top>
              <template #activator="{ on }">
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
            <v-tooltip bottom>
              <template #activator="{ on }">
                <v-btn
                  icon
                  :color="modified ? 'warning' : 'primary'"
                  :disabled="readonly"
                  v-on="on"
                  @click="save"
                >
                  <v-icon
                    v-text="modified ? 'mdi-content-save-alert' : 'mdi-content-save'"
                  />
                </v-btn>
              </template>
              <span>Save</span>
            </v-tooltip>
            <v-tooltip bottom>
              <template #activator="{ on }">
                <v-btn
                  icon
                  color="secondary"
                  :disabled="disableUndo"
                  v-on="on"
                  @click="undoChange"
                >
                  <v-icon>
                    mdi-undo
                  </v-icon>
                </v-btn>
              </template>
              <span>Undo</span>
            </v-tooltip>
            <v-tooltip bottom>
              <template #activator="{ on }">
                <v-btn
                  icon
                  color="secondary"
                  :disabled="disableRedo"
                  v-on="on"
                  @click="redoChange"
                >
                  <v-icon>
                    mdi-redo
                  </v-icon>
                </v-btn>
              </template>
              <span>Redo</span>
            </v-tooltip>
            <v-spacer />
            <v-tooltip bottom>
              <template #activator="{ on }">
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
            <v-btn
              elevation="0"
              color="info"
              :disabled="modified"
              @click="$emit('close')"
            >
              Done
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
    <v-row class="px-2 justify-center">
      <v-tabs
        v-model="tab"
        background-color="grey darken-2"
        slider-color="highlight"
        dark
        show-arrows
        align-with-title
      >
        <v-tab
          key="tab-0"
          class="font-weight-medium text-caption ml-2"
        >
          <v-badge
            color="error"
            dot
            :value="!editorInterface.basicModelValid.value"
          >
            General
          </v-badge>
        </v-tab>
        <v-tab
          v-for="(propKey, i) in fieldsToRender"
          :key="`tab-${i+1}`"
          class="font-weight-medium text-caption"
        >
          <v-badge
            color="error"
            dot
            :value="!editorInterface.complexModelValidation[propKey]"
          >
            {{ complexSchema.properties[propKey].title || propKey }}
          </v-badge>
        </v-tab>
      </v-tabs>
    </v-row>
    <v-row>
      <v-tabs-items
        v-model="tab"
        style="width: 100%;"
      >
        <v-tab-item
          key="tab-0"
          eager
        >
          <v-form
            v-model="basicModelValid"
            style="height: 70vh;"
            class="px-7 py-5 overflow-y-auto"
          >
            <v-jsf
              v-model="basicModel"
              :schema="basicSchema"
              :options="{...CommonVJSFOptions, hideReadOnly: true}"
              @change="vjsfListener"
            />
          </v-form>
        </v-tab-item>
        <v-tab-item
          v-for="(propKey, i) in fieldsToRender"
          :key="`tab-${i+1}`"
          eager
        >
          <v-card class="pa-2 px-1">
            <v-form
              v-model="complexModelValidation[propKey]"
              class="px-7"
            >
              <v-jsf-wrapper
                :transaction-tracker="transactionTracker"
                :prop-key="propKey"
                :editor-interface="editorInterface"
                :options="CommonVJSFOptions"
                :readonly="readonly"
              />
            </v-form>
          </v-card>
        </v-tab-item>
      </v-tabs-items>
    </v-row>
  </v-card>
</template>

<script lang="ts">
import type { JSONSchema7 } from 'json-schema';

import {
  defineComponent, ref, computed, ComputedRef, onMounted,
} from '@vue/composition-api';

import jsYaml from 'js-yaml';

import VJsf from '@koumoul/vjsf/lib/VJsf';
import '@koumoul/vjsf/lib/deps/third-party';
import '@koumoul/vjsf/lib/VJsf.css';

import { dandiRest } from '@/rest';
import store from '@/store';
import { DandiModel, isJSONSchema } from '@/utils/schema/types';
import { EditorInterface } from '@/utils/schema/editor';
import MeditorTransactionTracker from '@/utils/transactions';

import VJsfWrapper from '@/components/VJsfWrapper.vue';

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

export default defineComponent({
  name: 'Meditor',
  components: { VJsf, VJsfWrapper },
  setup() {
    const currentDandiset = computed(() => store.state.dandiset.dandiset);
    const id = computed(() => currentDandiset.value?.dandiset.identifier);
    const schema: ComputedRef<JSONSchema7> = computed(() => store.state.dandiset.schema);
    const model = computed(() => (currentDandiset.value ? currentDandiset.value.metadata : {}));
    const readonly = computed(() => !store.getters.dandiset.userCanModifyDandiset);

    const invalidPermissionSnackbar = ref(false);
    const tab = ref(null);

    const editorInterface = new EditorInterface(schema.value, model.value as DandiModel);
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
    const CommonVJSFOptions = computed(() => ({
      initialValidation: 'all',
      disableAll: readonly.value,
      autoFixArrayItems: false,
      childrenClass: 'px-2',
      fieldProps: {
        outlined: true,
        dense: true,
      },
      arrayItemCardProps: {
        outlined: true,
        dense: true,
      },
      editMode: 'inline',
      hideReadOnly: true,
    }));

    const transactionTracker = new MeditorTransactionTracker(editorInterface);

    // undo/redo functionality
    function undoChange() {
      transactionTracker.undo();
    }
    function redoChange() {
      transactionTracker.redo();
    }
    const disableUndo = computed(
      () => readonly.value || !transactionTracker.areTransactionsBehind(),
    );
    const disableRedo = computed(
      () => readonly.value || !transactionTracker.areTransactionsAhead(),
    );
    const vjsfListener = () => transactionTracker.add(basicModel.value, false);
    const modified = computed(() => transactionTracker.isModified());

    async function save() {
      if (!id.value || !currentDandiset.value?.version) {
        return;
      }
      const dandiset = editorInterface.getModel();

      try {
        const { status, data } = await dandiRest.saveDandiset(
          id.value, currentDandiset.value.version, dandiset,
        );

        if (status === 200) {
          // wait 0.5 seconds to give the celery worker some time to finish validation
          setTimeout(async () => {
            await store.dispatch.dandiset.fetchDandiset({
              identifier: data.dandiset.identifier,
              version: data.version,
            });
            transactionTracker.reset();
          }, 500);
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
      const currentModel = editorInterface.getModel();
      return yamlOutput.value ? jsYaml.dump(currentModel) : JSON.stringify(currentModel, null, 2);
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

    const fieldsToRender = Object.keys(complexSchema.properties as any).filter(
      (p) => renderField((complexSchema as any).properties[p]),
    );

    onMounted(() => {
      window.addEventListener('beforeunload', (e) => {
        // display a confirmation prompt if attempting to navigate away from the
        // page with unsaved changes in the meditor
        if (modified.value) {
          e.preventDefault();
          // Required for Chrome-based browsers -
          // see https://developer.mozilla.org/en-US/docs/Web/API/WindowEventHandlers/onbeforeunload#example
          e.returnValue = 'test';
        }
      });
    });

    return {
      allModelsValid: modelValid,
      tab,
      schema,
      model,
      readonly,

      basicSchema,
      basicModel,
      basicModelValid,
      vjsfListener,

      complexSchema,
      complexModel,
      complexModelValid,
      complexModelValidation,

      invalidPermissionSnackbar,
      fieldsToRender,
      save,
      download,

      modified,
      undoChange,
      redoChange,
      disableUndo,
      disableRedo,

      CommonVJSFOptions,

      setComplexModelProp,

      editorInterface,
      transactionTracker,
    };
  },
});
</script>
