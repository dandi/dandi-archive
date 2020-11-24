/* eslint no-console: 0 */
/* eslint no-throw-literal: 0 */
import Vue from 'vue';

// Create a component to hold the feature toggles reactively
// This object can be mutated at runtime to enable/disable feature toggles
const featureToggles = new Vue({
  data() {
    return {
      DJANGO_API: false,
    };
  },
});

// Register the feature toggles as computed properties on all components
// Now feature toggles are available on all components and templates without any imports
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
function enable(featureToggle) {
  if (!(featureToggle in featureToggles)) {
    throw `Feature toggle ${featureToggle} is not defined`;
  }
  featureToggles[featureToggle] = true;
  console.log(`Feature toggle '${featureToggle}' enabled`);
}

/** Disables a feature toggle. Only usable from the console. */
function disable(featureToggle) {
  if (!(featureToggle in featureToggles)) {
    throw `Feature toggle ${featureToggle} is not defined`;
  }
  featureToggles[featureToggle] = false;
  console.log(`Feature toggle '${featureToggle}' disabled`);
}

// Register enable and disable on the window object so they are accessible from the console
window.enable = enable;
window.disable = disable;
