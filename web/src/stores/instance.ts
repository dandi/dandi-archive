import { defineStore } from 'pinia';

import { dandiRest } from '@/rest';
import type { Info } from '@/types';

// Values of DJANGO_DANDI_INSTANCE_NAME for the DANDI-operated deployments,
// reported by the server at /api/info/.
const PRODUCTION_INSTANCE_NAME = 'DANDI';
const SANDBOX_INSTANCE_NAME = 'DANDI-SANDBOX';

// Shared by all callers of load() so the request is only made once per session.
let infoRequest: Promise<Info> | undefined;

interface State {
  info: Info | null;
}

export const useInstanceStore = defineStore('instance', {
  state: (): State => ({
    info: null,
  }),
  getters: {
    instanceName: (state) => state.info?.instance_config.instance_name,
    // Until /api/info/ has been fetched successfully, the instance is not considered
    // production or sandbox, so features gated on these getters fail closed.
    isProduction(): boolean {
      return this.instanceName === PRODUCTION_INSTANCE_NAME;
    },
    isSandbox(): boolean {
      return this.instanceName === SANDBOX_INSTANCE_NAME;
    },
  },
  actions: {
    async load() {
      if (this.info) {
        return;
      }
      if (infoRequest === undefined) {
        infoRequest = dandiRest.info();
      }
      try {
        this.info = await infoRequest;
      } catch (error) {
        // Leave the instance identity unknown; clearing the shared request
        // lets a later call retry.
        console.error('Error fetching server instance info:', error);
        infoRequest = undefined;
      }
    },
  },
});
