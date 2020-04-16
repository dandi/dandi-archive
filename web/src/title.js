import Vue from 'vue';

const setTitle = (el, binding) => {
  if (binding && binding.value) {
    document.title = `${binding.value} - DANDI Archive`;
  } else {
    document.title = 'DANDI Archive';
  }
}

Vue.directive('title', {
  inserted: setTitle,
  update: setTitle,
});
