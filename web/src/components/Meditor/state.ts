import { computed, ref, Ref } from 'vue';
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
        if (!state.editorInterface) {
          throw new Error('Unexpected state change');
        }
        state.editorInterface[key as keyof EditorInterface] = value;
      });
    }
  },
});

const open = ref(false); // whether or not the Meditor is open
const tab: Ref<string | null> = ref(null); // the current tab of the meditor
function setTab(tabKey?: string) {
  if (!tabKey || !editorInterface.value?.fieldsToRender.includes(tabKey)) {
    tab.value = `tab-0`;
  } else {
    tab.value = `tab-${tabKey}`;
  }
}

const pendingNewItem: Ref<{ propKey: string; item: Record<string, unknown> } | null> = ref(null);
function queueNewItem(propKey: string, item: Record<string, unknown>) {
  pendingNewItem.value = { propKey, item };
}

export {
  editorInterface,
  open,
  tab,
  setTab,
  pendingNewItem,
  queueNewItem,
};
