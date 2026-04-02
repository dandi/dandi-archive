import { defineStore } from 'pinia';

import { dandiRest } from '@/rest';

interface InstanceState {
  instanceName: string;
  instanceIdentifier: string | null;
  instanceUrl: string | null;
  loaded: boolean;
}

export const useInstanceStore = defineStore('instance', {
  state: (): InstanceState => ({
    instanceName: '',
    instanceIdentifier: null,
    instanceUrl: null,
    loaded: false,
  }),
  actions: {
    async fetchInstanceInfo() {
      if (this.loaded) {
        return;
      }
      const info = await dandiRest.info();
      this.instanceName = info.instance_config.instance_name;
      this.instanceIdentifier = info.instance_config.instance_identifier;
      this.instanceUrl = info.instance_config.instance_url;
      this.loaded = true;
    },
  },
});
