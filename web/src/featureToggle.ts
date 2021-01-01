/* eslint no-console: 0 */
import Vue from 'vue';
import { reactive } from '@vue/composition-api';

// Declare additions to the global `window` object
declare global {
  interface Window {
    enable: (toggle: string) => void,
    disable: (toggle: string) => void,
  }
}

// Create a component to hold the feature toggles reactively
// This object can be mutated at runtime to enable/disable feature toggles
const featureToggles = reactive({
  DJANGO_API: false,
});

// Used to narrow string types
function isToggle(toggle: string): toggle is keyof (typeof featureToggles) {
  return Object.keys(featureToggles).includes(toggle);
}

// Register the feature toggles as computed properties on all components
// Now feature toggles are available on all components and templates without any imports
// TODO: Convert this to use composition API.
Vue.mixin({
  computed: {
    DJANGO_API() {
      return featureToggles.DJANGO_API;
    },
  },
});

export default featureToggles;

// We also want to support toggling feature toggles in branch previews and in master
// These functions are made available globally so they can be called from the console

/** Enables a feature toggle. Only usable from the console. */
function enable(featureToggle: string) {
  if (!isToggle(featureToggle)) {
    throw new Error(`Feature toggle ${featureToggle} is not defined`);
  }

  featureToggles[featureToggle] = true;
  console.log(`Feature toggle '${featureToggle}' enabled`);
}

/** Disables a feature toggle. Only usable from the console. */
function disable(featureToggle: string) {
  if (!isToggle(featureToggle)) {
    throw new Error(`Feature toggle ${featureToggle} is not defined`);
  }

  featureToggles[featureToggle] = false;
  console.log(`Feature toggle '${featureToggle}' disabled`);
}

// Register enable and disable on the window object so they are accessible from the console
window.enable = enable;
window.disable = disable;
