import type { App, DirectiveBinding } from 'vue'

import { useInstanceStore } from '@/stores/instance';

function getTitle(): string {
  const instanceStore = useInstanceStore();
  return instanceStore.instanceName ? `${instanceStore.instanceName} Archive` : 'DANDI Archive';
}

// Function to set the page title based on the directive's binding value
const setPageTitle = (el: HTMLElement, binding: DirectiveBinding) => {
  const title = getTitle();
  if (binding?.value) {
    document.title = `${binding.value} - ${title}`;
  } else {
    document.title = title;
  }
};

const directives = {
  'page-title': {
    // Use mounted and updated lifecycle hooks instead of inserted and unbind
    mounted: setPageTitle,
    updated: setPageTitle,
    beforeUnmount: () => {
      document.title = getTitle();
    },
  }
}

export function registerDirectives(app: App) {
  Object.entries(directives).forEach(([name, directive]) => {
    app.directive(name, directive);
  });
}
