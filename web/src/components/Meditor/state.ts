import Vue from 'vue';
import { computed } from '@vue/composition-api';
import { EditorInterface } from './editor';

const state = {
  editorInterface: {} as EditorInterface,
};

const editorInterface = computed({
  get: () => state.editorInterface,
  set: (newVal: EditorInterface) => {
    if (Object.keys(state.editorInterface).length === 0) {
      // If editorInterface hasn't been instantiated yet, just assign the new instance to it
      state.editorInterface = newVal;
    } else {
      // Otherwise, mutate the existing instance's properties using Vue.set
      Object.entries(newVal).forEach(([key, value]) => {
        Vue.set(state.editorInterface, key, value);
      });
    }
  },
});

export {
  editorInterface,
};
