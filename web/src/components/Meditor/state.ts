import Vue from 'vue';
import { computed } from '@vue/composition-api';
import { EditorInterface } from './editor';

const state = {
  editorInterface: null as EditorInterface | null,
};

const editorInterface = computed({
  get: () => state.editorInterface,
  set: (newVal) => {
    if (!state.editorInterface) {
      // If editorInterface hasn't been instantiated yet, just assign the new instance to it
      state.editorInterface = newVal;
    } else {
      if (!newVal) {
        return;
      }
      // Otherwise, mutate the existing instance's properties using Vue.set
      Object.entries(newVal).forEach(([key, value]) => {
        Vue.set(state.editorInterface as EditorInterface, key, value);
      });
    }
  },
});

export {
  editorInterface,
};
