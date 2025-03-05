import { computed, ref } from 'vue';
import type { EditorInterface } from './editor';

// NOTE: it would be better to use a single ref here instead of separate state/computed
// variables, but doing so introduces a strange bug where editorInterface.basicModel is
// un-reffed immediately after instantiation. This does not occur when using a computed
// variable with a separate state object, so we do that here as a workaround.
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
      // Otherwise, mutate the existing instance's properties
      Object.entries(newVal).forEach(([key, value]) => {
        // @ts-expect-error TODO: Fix this
        (state.editorInterface as EditorInterface)[key] = value;
      });
    }
  },
});

const open = ref(false); // whether or not the Meditor is open

export {
  editorInterface,
  open,
};
