<!-- eslint-disable vue/multi-word-component-names -->
<template>
  <v-dialog
    v-model="open"
    max-width="85vw"
  >
    <v-card
      v-if="schema && model && editorInterface"
      v-page-title="model.name"
      class="overflow-hidden"
      min-height="70vh"
    >
      <!-- TODO: fix and re-enable this -->
      <!-- <v-dialog
        v-model="loadFromLocalStoragePrompt"
        persistent
        max-width="60vh"
      >
        <v-card class="pb-3">
          <v-card-title class="text-h5 font-weight-light">
            Attention
          </v-card-title>
          <v-divider class="my-3" />
          <v-card-text>
            You have previously edited this dandiset and have unsaved data.
          </v-card-text>
          <v-card-text>
            Would you like to load that data?
          </v-card-text>

          <v-card-text class="font-weight-bold">
            WARNING: this will overwrite any changes that were made by others since your last edit.
          </v-card-text>

          <v-card-actions>
            <v-btn
              color="error"
              depressed
              @click="loadDataFromLocalStorage()"
            >
              Yes
            </v-btn>
            <v-btn
              depressed
              @click="discardDataFromLocalStorage()"
            >
              No, discard it
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog> -->
      <v-card
        class="mb-2"
        variant="outlined"
      >
        <v-card-actions class="pt-0">
          <v-tooltip location="top">
            <template #activator="{ props }">
              <v-icon
                start
                :color="modelValid ? 'success' : 'error'"
                v-bind="props"
              >
                <template v-if="modelValid">
                  mdi-checkbox-marked-circle
                </template>
                <template v-else>
                  mdi-alert-circle
                </template>
              </v-icon>
            </template>
            <template v-if="modelValid">
              All metadata for this dandiset is valid.
            </template>
            <template v-else>
              There are errors in the metadata for this Dandiset.
            </template>
          </v-tooltip>
          <v-tooltip location="bottom">
            <template #activator="{ props }">
              <v-btn
                icon
                :color="modified ? 'warning' : 'primary'"
                :disabled="readonly || !modified"
                v-bind="props"
                @click="save"
              >
                <v-icon>{{ modified ? 'mdi-content-save-alert' : 'mdi-content-save' }}</v-icon>
              </v-btn>
            </template>
            <span>Save</span>
          </v-tooltip>
          <v-tooltip location="bottom">
            <template #activator="{ props }">
              <v-btn
                icon
                color="secondary"
                :disabled="disableUndo"
                v-bind="props"
                @click="undoChange"
              >
                <v-icon>
                  mdi-undo
                </v-icon>
              </v-btn>
            </template>
            <span>Undo</span>
          </v-tooltip>
          <v-tooltip location="bottom">
            <template #activator="{ props }">
              <v-btn
                icon
                color="secondary"
                :disabled="disableRedo"
                v-bind="props"
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
          <v-tooltip location="bottom">
            <template #activator="{ props }">
              <v-btn
                icon
                v-bind="props"
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
      <v-tabs
        v-model="tab"
        bg-color="grey-darken-2"
        slider-color="highlight"
        show-arrows
        align-tabs="title"
      >
        <v-tab
          value="tab-0"
          class="font-weight-medium text-caption ml-2"
        >
          <v-badge
            color="error"
            dot
            :model-value="!basicModelValid"
          >
            General
          </v-badge>
        </v-tab>
        <v-tab
          v-for="(propKey, i) in fieldsToRender"
          :key="`tab-${i+1}`"
          :value="`tab-${i+1}`"
          class="font-weight-medium text-caption"
        >
          <v-badge
            color="error"
            dot
            :model-value="!complexModelValidation[propKey]"
          >
            {{ getSchemaTitle(propKey) }}
          </v-badge>
        </v-tab>
      </v-tabs>
      <v-tabs-window
        v-model="tab"
      >
        <v-tabs-window-item
          eager
          value="tab-0"
        >
          <v-defaults-provider :defaults="VJSFVuetifyDefaultProps">
            <v-form
              v-model="basicModelValid"
              style="height: 70vh;"
              class="px-7 py-5 overflow-y-auto"
            >
              <v-jsf
                :key="`
            basicModel-${editorInterface.transactionTracker.getTransactionPointer()}
          `"
                v-model="basicModel"
                :schema="basicSchema"
                :options="CommonVJSFOptions"
                @update:model-value="vjsfListener"
              />
            </v-form>
          </v-defaults-provider>
        </v-tabs-window-item>
      </v-tabs-window>
      <v-tabs-window
        v-for="(propKey, i) in fieldsToRender"
        :key="`tab-window-${i+1}`"
        v-model="tab"
      >
        <v-tabs-window-item
          eager
          :value="`tab-${i+1}`"
        >
          <v-card class="pa-2 px-1">
            <v-form
              class="px-7"
            >
              <v-jsf-wrapper
                :prop-key="propKey"
                :options="CommonVJSFOptions"
                :readonly="readonly"
              />
            </v-form>
          </v-card>
        </v-tabs-window-item>
      </v-tabs-window>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import type { JSONSchema7 } from 'json-schema';

import type { ComputedRef } from 'vue';
import { ref, computed, watchEffect } from 'vue';

import jsYaml from 'js-yaml';
import axios from 'axios';

import VJsf from '@koumoul/vjsf';

import { dandiRest } from '@/rest';
import { useDandisetStore } from '@/stores/dandiset';
import type { DandiModel } from './types';
import { isJSONSchema } from './types';
import { EditorInterface } from './editor';
import { validateDandisetMetadata, VJSFVuetifyDefaultProps } from './utils';

import {
  clearLocalStorage,
  // dataInLocalStorage,
  // getModelLocalStorage,
  // getTransactionPointerLocalStorage,
  // getTransactionsLocalStorage,
} from './localStorage';
import VJsfWrapper from './VJsfWrapper.vue';
import { editorInterface, open } from './state';

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

const store = useDandisetStore();

const currentDandiset = computed(() => store.dandiset);
const id = computed(() => currentDandiset.value?.dandiset.identifier);
const schema: ComputedRef<JSONSchema7> = computed(() => store.schema);
const model = computed(() => currentDandiset.value?.metadata);
const readonly = computed(() => !store.userCanModifyDandiset);
// const isDataInLocalStorage = computed(
//   () => (model.value ? dataInLocalStorage(model.value.id) : false),
// );

const invalidPermissionSnackbar = ref(false);
const tab = ref(null);
// const loadFromLocalStoragePrompt = ref(false);

editorInterface.value = new EditorInterface(schema.value, model.value as DandiModel);
const {
  modelValid,
  basicSchema,
  basicModel,
  basicModelValid,
  complexSchema,
  complexModelValidation,
  transactionTracker,
} = editorInterface.value;
const CommonVJSFOptions = computed(() => ({
  // Always validate the metadata immediately upong the meditor opening
  initialValidation: 'always',
  // Do not add the default value for a field if it is missing
  defaultOn: 'never',
  // Do not allow the user to modify the form if it is read-only
  readOnly: readonly.value,
  // Hide the read-only properties in the schema
  readOnlyPropertiesMode: 'hide',
}));


watchEffect(() => {
  if (schema.value && editorInterface.value) {
    validateDandisetMetadata(editorInterface.value)
  }
});

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
  if (!id.value || !model.value || !currentDandiset.value?.version) {
    return;
  }
  const dandiset = editorInterface.value?.getModel();

  try {
    const { status, data } = await dandiRest.saveDandiset(
      id.value, currentDandiset.value.version, dandiset,
    );

    if (status === 200) {
      clearLocalStorage(model.value.id);
      // wait 0.5 seconds to give the celery worker some time to finish validation
      setTimeout(async () => {
        await store.fetchDandiset({
          identifier: data.dandiset.identifier,
          version: data.version,
        });
        transactionTracker.reset();
      }, 500);
    }
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 403) {
      invalidPermissionSnackbar.value = true;
    }

    throw error;
  }
}

// TODO: Add back UI to toggle YAML vs JSON
const yamlOutput = ref(false);
const contentType = computed(() => (yamlOutput.value ? 'text/yaml' : 'application/json'));
const output = computed(() => {
  const currentModel = editorInterface.value?.getModel();
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

function getSchemaTitle(propKey: string) {
  const properties = complexSchema?.properties as any;
  return properties ? properties[propKey].title || propKey : propKey;
}

const fieldsToRender = Object.keys(complexSchema.properties as any).filter(
  (p) => renderField((complexSchema as any).properties[p]),
);

// TODO: fix and re-enable this
// function loadDataFromLocalStorage() {
//   if (!model.value) {
//     return;
//   }
//   // load previous meditor data from localStorage
//   editorInterface.value?.setModel(getModelLocalStorage(model.value.id));
//   editorInterface.value?.transactionTracker.setTransactions(
//     getTransactionsLocalStorage(model.value.id),
//   );
//   editorInterface.value?.transactionTracker.setTransactionPointer(
//     getTransactionPointerLocalStorage(model.value.id),
//   );
//   loadFromLocalStoragePrompt.value = false;
// }
// function discardDataFromLocalStorage() {
//   if (!model.value) {
//     return;
//   }
//   clearLocalStorage(model.value.id);
//   loadFromLocalStoragePrompt.value = false;
// }
// onMounted(() => {
//   // On mount, detect if there is unsaved data stored in local storage and ask the user
//   // if they would like to restore it
//   if (isDataInLocalStorage.value) {
//     loadFromLocalStoragePrompt.value = true;
//   }
// });

</script>

<style scoped>
/***
 Disable all Vuetify component transitions in the Meditor.
 Vuetify's default tab transitions cause VJSF to glitch out and
 flicker when tabs change.
***/
div[class^="v-"]{
  transition: none !important;
}
</style>
