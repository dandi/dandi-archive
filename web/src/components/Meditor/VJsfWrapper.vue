<template>
  <div v-if="editorInterface && editorInterface.complexSchema">
    <v-row class="d-flex justify-space-between">
      <v-col cols="6">
        <div
          style="height: 60vh;"
          class="overflow-y-auto"
        >
          <v-form v-model="formValid">
            <!-- Note: use transaction stack pointer as key to force vjsf rerender on undo/redo -->
            <v-jsf
              v-if="index >= 0"
              :key="`
                ${propKey}-${index}-${editorInterface.transactionTracker.getTransactionPointer()}
              `"
              class="my-6"
              :model-value="currentItem"
              :schema="schema"
              :options="options"
              @update:model-value="currentItem = $event"
            />
          </v-form>
        </div>
        <div style="height: 10vh;">
          <v-divider class="my-2" />
          <div class="d-flex align-center justify-space-between mx-2">
            <v-btn
              elevation="0"
              color="white"
              class="text-grey-darken-2 font-weight-medium"
              @click="clearForm"
            >
              Clear Form
            </v-btn>
            <v-btn
              v-if="index === -1"
              class="bg-grey-darken-3 text-white"
              elevation="0"
              @click="createNewItem"
            >
              <span class="mr-1">Add Item</span>
              <v-icon>mdi-arrow-right</v-icon>
            </v-btn>
            <v-btn
              v-else
              class="bg-grey-darken-3 text-white"
              elevation="0"
              :disabled="!formValid"
              @click="saveItem"
            >
              <span class="mr-1">Save Item</span>
              <v-icon>mdi-arrow-right</v-icon>
            </v-btn>
          </div>
        </div>
      </v-col>
      <v-col
        :style="`background-color: ${theme.current.value.colors.dropzone}; height: 70vh;`"
        class="overflow-y-auto"
        cols="6"
      >
        <v-sheet
          v-if="editorInterface.complexSchema.properties"
          class="ma-4"
        >
          <draggable
            v-model="currentModel"
            item-key="id"
          >
            <template #item="{ element: item, index: i }">
              <v-card
                :key="i"
                variant="outlined"
              >
                <div class="pa-3 d-flex align-center justify-space-between">
                  <span class="d-inline text-truncate text-subtitle-1">
                    <v-icon>mdi-drag-horizontal-variant</v-icon>
                    <span :class="index === i ? 'accent--text' : undefined">
                      {{ item.name || item.identifier || item.id }}
                      {{ index === i && isModified ? '*' : undefined }}
                    </span>
                  </span>
                  <span style="min-width: 31%;">
                    <span v-if="!readonly">
                      <v-btn
                        variant="text"
                        size="small"
                        @click="removeItem(i)"
                      >
                        <v-icon
                          color="error"
                          start
                        >
                          mdi-minus-circle
                        </v-icon>
                        <span class="font-weight-regular">
                          Remove
                        </span>
                      </v-btn>
                    </span>
                    <span>
                      <v-btn
                        :disabled="index === i"
                        variant="text"
                        size="small"
                        @click="selectExistingItem(i)"
                      >
                        <v-icon
                          color="info"
                          start
                        >
                          mdi-{{ readonly ? 'eye' : 'pencil' }}
                        </v-icon>
                        <span class="font-weight-regular">
                          {{ readonly ? 'View' : 'Edit' }}
                        </span>
                      </v-btn>
                    </span>
                  </span>
                </div>
              </v-card>
            </template>
          </draggable>
        </v-sheet>
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import VJsf from '@koumoul/vjsf';
import draggable from 'vuedraggable';
import { isEqual } from 'lodash';
import { useTheme } from 'vuetify';
import type { JSONSchema7 } from 'json-schema';

import type { DandiModel } from './types';
import { editorInterface } from './state';

const props = defineProps({
  propKey: {
    type: String,
    required: true,
  },
  options: {
    type: Object,
    required: true,
  },
  readonly: {
    type: Boolean,
    required: true,
  },
});

const theme = useTheme();

const index = ref(-1); // index of item currently being edited
const currentItem = ref({}); // the item currently being edited
const formValid = ref(false); // whether or not the current item being edited is valid

// extracts the subschema for the given propKey
const schema = computed(
  // @ts-expect-error - computed type
  () => editorInterface.value?.complexSchema.properties?.[props.propKey].items as JSONSchema7
);

const currentModel = computed({
  get: () => editorInterface.value?.complexModel[props.propKey] as DandiModel[],
  set: (newModel: any) => {
    editorInterface.value?.setComplexModelProp(props.propKey, newModel);
    editorInterface.value?.transactionTracker.add(editorInterface.value.complexModel, true);
  },
});

// Update current item if model changed
watch(currentModel, (val) => {
  if (index.value >= 0) {
    currentItem.value = val[index.value];
  }
});

// whether the current form has been edited and requires saving
const isModified = computed(() => !isEqual(
  currentItem.value,
  currentModel.value[index.value],
));

function clearForm() {
  index.value = -1;
  currentItem.value = {};
}

function createNewItem() {
  currentModel.value = [...currentModel.value, currentItem.value];
  index.value = currentModel.value.length - 1;
}

function saveItem() {
  // write the item currently being edited into the schema model
  const newModel = [...currentModel.value];
  newModel[index.value] = currentItem.value;
  currentModel.value = newModel;
  clearForm();
}

function removeItem(index_to_remove: number) {
  // remove an item from the schema model
  if (index.value === index_to_remove) {
    index.value = -1;
    currentItem.value = {};
  }

  // Create new value and set
  const currentValue = [...currentModel.value];
  currentValue.splice(index_to_remove, 1);
  currentModel.value = currentValue;
}

function selectExistingItem(new_index: number) {
  index.value = new_index;
  // make a deep copy so the schema model isn't modified until this is saved
  currentItem.value = JSON.parse(JSON.stringify(
    currentModel.value,
  ))[new_index];
}
</script>
