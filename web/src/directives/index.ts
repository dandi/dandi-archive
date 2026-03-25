import type { App, DirectiveBinding } from 'vue'

const TITLE = 'DANDI Archive';

// Function to set the page title based on the directive's binding value
const setPageTitle = (el: HTMLElement, binding: DirectiveBinding) => {
  if (binding?.value) {
    document.title = `${binding.value} - ${TITLE}`;
  } else {
    document.title = TITLE;
  }
};

const directives = {
  'page-title': {
    // Use mounted and updated lifecycle hooks instead of inserted and unbind
    mounted: setPageTitle,
    updated: setPageTitle,
    beforeUnmount: () => {
      document.title = TITLE;
    },
  }
}

export function registerDirectives(app: App) {
  Object.entries(directives).forEach(([name, directive]) => {
    app.directive(name, directive);
  });
}
