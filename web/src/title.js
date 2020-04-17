import Vue from 'vue';

const setPageTitle = (el, binding) => {
  if (binding && binding.value) {
    document.title = `${binding.value} - DANDI Archive`;
  } else {
    document.title = 'DANDI Archive';
  }
}

Vue.directive('page-title', {
  inserted: setPageTitle,
  update: setPageTitle,
});
