import Vue from 'vue';

import type { DirectiveBinding } from 'vue/types/options';

const TITLE = 'DANDI Archive';

const setPageTitle = (el: HTMLElement, binding: DirectiveBinding) => {
  if (binding?.value) {
    document.title = `${binding.value} - ${TITLE}`;
  } else {
    document.title = TITLE;
  }
};

Vue.directive('page-title', {
  // using inserted rather than bind causes less flickering
  inserted: setPageTitle,
  update: setPageTitle,
  unbind: () => { document.title = TITLE; },
});
