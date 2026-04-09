import { defineStore } from 'pinia';

import { dandiRest } from '@/rest';

interface InstanceState {
  instanceName: string;
  instanceIdentifier: string | null;
  instanceUrl: string | null;
  loaded: boolean;
  _fetchPromise: Promise<void> | null;
}

export const useInstanceStore = defineStore('instance', {
  state: (): InstanceState => ({
    instanceName: '',
    instanceIdentifier: null,
    instanceUrl: null,
    loaded: false,
    _fetchPromise: null,
  }),
  actions: {
    async fetchInstanceInfo() {
      if (this.loaded) {
        return;
      }
      if (this._fetchPromise) {
        return this._fetchPromise;
      }
      this._fetchPromise = this._doFetch();
      return this._fetchPromise;
    },
    async _doFetch() {
      const info = await dandiRest.info();
      this.instanceName = info.instance_config.instance_name;
      this.instanceIdentifier = info.instance_config.instance_identifier;
      this.instanceUrl = info.instance_config.instance_url;
      this.loaded = true;
    },
  },
});
