<template>
  <v-progress-linear
    v-if="!publishDandiset"
    indeterminate
  />
  <PublishFileBrowser
    v-else
    :identifier="identifier"
    :version="version"
  />
</template>

<script>
import store from '@/store';
import { draftVersion } from '@/utils/constants';
import PublishFileBrowser from './PublishFileBrowser.vue';

export default {
  name: 'FileBrowser',
  components: {
    PublishFileBrowser,
  },
  props: {
    identifier: {
      type: String,
      required: true,
    },
    version: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      draftVersion,
    };
  },
  computed: {
    publishDandiset() {
      return store.state.dandiset.publishDandiset;
    },
  },
  async created() {
    // Don't extract publishDandiset, for reactivity
    const { identifier, version } = this;
    if (!this.publishDandiset) {
      this.fetchPublishDandiset({ identifier, version });
    }
  },
  methods: {
    fetchPublishDandiset() {
      store.dispatch.fetchPublishDandiset({
        identifier: this.identifier,
        version: this.version,
      });
    },
  },
};
</script>
