import Vue from 'vue';

const TITLE = 'DANDI Archive';

const setPageTitle = (el, binding) => {
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
  unbind: () => document.title = TITLE
});
