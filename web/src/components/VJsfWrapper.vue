<template>
  <v-row class="d-flex justify-space-evenly">
    <v-col cols="6">
      <div
        style="height: 75vh;"
        class="overflow-y-auto"
      >
        <!-- Note: use the transaction stack pointer as key to force vjsf rerender on undo/redo -->
        <v-jsf
          :key="`${propKey}-${index}-${transactionTracker.transactionPointer}`"
          class="my-6"
          :value="currentItem"
          :schema="schema"
          :options="options"
          @input="currentItem=$event"
          @change="formListener"
        />
        <v-divider />
        <div
          style="height: 10vh"
          class="d-flex align-center justify-space-between"
        >
          <v-btn
            elevation="0"
            color="white"
            class="text--darken-2 grey--text font-weight-medium"
            @click="clearForm()"
          >
            Clear Form
          </v-btn>
          <v-btn
            v-if="index === -1"
            dark
            elevation="0"
            @click="createNewItem()"
          >
            <span class="mr-1">Add Item</span>
            <v-icon>mdi-arrow-right</v-icon>
          </v-btn>
          <v-btn
            v-else
            dark
            elevation="0"
            @click="saveItem(propKey)"
          >
            <span class="mr-1">Save Item</span>
            <v-icon>mdi-arrow-right</v-icon>
          </v-btn>
        </div>
      </div>
    </v-col>
    <v-col
      :style="`
        background-color: ${
        $vuetify.theme.themes[$vuetify.theme.isDark ? 'dark' : 'light'].dropzone
      }; height: 75vh;
        `"
      class="overflow-y-auto"
      cols="6"
    >
      <v-sheet class="ma-4">
        <v-jsf
          :value="editorInterface.complexModel[propKey]"
          :schema="editorInterface.complexSchema.properties[propKey]"
          :options="options"
          @input="setComplexModelProp($event)"
        >
          <template slot-scope="slotProps">
            <v-card
              outlined
              class="d-flex flex-column"
            >
              <draggable
                @update="reorderItem($event)"
              >
                <v-card
                  v-for="(item, i) in slotProps.value"
                  :key="i"
                  outlined
                >
                  <div class="pa-3 d-flex align-center justify-space-between">
                    <span class="d-inline text-truncate text-subtitle-1">
                      <v-icon>mdi-drag-horizontal-variant</v-icon>
                      <span :class="index === i ? 'accent--text' : undefined">
                        {{ item.name || item.identifier || item.id }}
                        {{ index === i ? '*' : undefined }}
                      </span>
                    </span>
                    <span style="min-width: 31%;">
                      <span>
                        <v-btn
                          text
                          small
                          @click="removeItem(i)"
                        >
                          <v-icon
                            color="error"
                            left
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
                          text
                          small
                          @click="selectExistingItem(i)"
                        >
                          <v-icon
                            color="info"
                            left
                          >
                            mdi-pencil
                          </v-icon>
                          <span class="font-weight-regular">
                            Edit
                          </span>
                        </v-btn>
                      </span>
                    </span>
                  </div>
                </v-card>
              </draggable>
            </v-card>
          </template>
        </v-jsf>
      </v-sheet>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import {
  computed, defineComponent, ref, PropType, watch,
} from '@vue/composition-api';

import VJsf from '@koumoul/vjsf/lib/VJsf';
import '@koumoul/vjsf/lib/deps/third-party';
import '@koumoul/vjsf/lib/VJsf.css';
import { EditorInterface } from '@/utils/schema/editor';
import { DandiModel } from '@/utils/schema/types';
import MeditorTransactionTracker from '@/utils/transactions';

export default defineComponent({
  name: 'VjsfWrapper',
  components: { VJsf },
  props: {
    editorInterface: {
      type: Object as PropType<EditorInterface>,
      required: true,
    },
    transactionTracker: {
      type: Object as PropType<MeditorTransactionTracker>,
      required: true,
    },
    propKey: {
      type: String,
      required: true,
    },
    options: {
      type: Object,
      required: true,
    },
  },
  setup(props) {
    const index = ref(-1); // index of item currently being edited
    const currentItem = ref({}); // the item currently being edited
    const isNewItem = ref(true);

    // extracts the subschema for the given propKey
    const schema = computed(
      // @ts-ignore
      () => props.editorInterface.complexSchema.properties[props.propKey].items,
    );

    watch(() => props.editorInterface.complexModel[props.propKey], () => {
      if (index.value >= 0) {
        currentItem.value = (props.editorInterface.complexModel as any)[props.propKey][index.value];
      }
    });

    function setComplexModelProp(event: DandiModel): void {
      const currentValue = [...(props.editorInterface.complexModel[props.propKey] as any)] as any;
      if (index.value >= 0) {
        currentValue[index.value] = { ...(currentValue[index.value] as DandiModel), ...event };
      } else {
        index.value = currentValue.push(event);
      }
      props.editorInterface.setComplexModelProp(props.propKey, currentValue);
    }

    function createNewItem() {
      // @ts-ignore
      const currentModel = [...props.editorInterface.complexModel[props.propKey]];
      currentModel.push(currentItem.value);
      // @ts-ignore
      props.editorInterface.setComplexModelProp(props.propKey, currentModel);
      index.value = currentModel.length - 1;

      // record a transaction
      props.transactionTracker.add(props.editorInterface.complexModel, true);
    }

    function saveItem() {
      // write the item currently being edited into the schema model

      // @ts-ignore
      const currentModel = [...props.editorInterface.complexModel[props.propKey]];
      currentModel[index.value] = currentItem.value;
      // @ts-ignore
      props.editorInterface.setComplexModelProp(props.propKey, currentModel);

      // record a transaction
      props.transactionTracker.add(props.editorInterface.complexModel, true);
    }

    function removeItem(index_to_remove: number) {
      // remove an item from the schema model
      if (index.value === index_to_remove) {
        index.value = -1;
        currentItem.value = {};
      }
      const currentValue = [...(props.editorInterface.complexModel[props.propKey] as any)] as any;
      currentValue.splice(index_to_remove, 1);
      props.editorInterface.setComplexModelProp(props.propKey, currentValue);

      // record a transaction
      props.transactionTracker.add(props.editorInterface.complexModel, true);
    }

    function selectExistingItem(new_index: number) {
      index.value = new_index;
      // make a deep copy so the schema model isn't modified until this is saved
      currentItem.value = JSON.parse(JSON.stringify(
        props.editorInterface.complexModel[props.propKey],
      ))[new_index];
    }

    function clearForm() {
      index.value = -1;
      currentItem.value = {};
    }

    function editItem(event: DandiModel) {
      // select an item from the model to be edited
      currentItem.value = JSON.parse(JSON.stringify(event));
    }

    function reorderItem(event: any) {
      // const { oldIndex, newIndex } = event;
      // @ts-ignore
      // const item = props.editorInterface.complexModel[props.propKey][oldIndex];
    }

    function formListener() {
      // record a new transaction whenever the current item is modified
      props.transactionTracker.add(props.editorInterface.complexModel, true);
    }

    return {
      index,
      setComplexModelProp,
      removeItem,
      currentItem,
      createNewItem,
      saveItem,
      schema,
      isNewItem,
      selectExistingItem,
      clearForm,
      editItem,
      reorderItem,
      formListener,
    };
  },
});
</script>
