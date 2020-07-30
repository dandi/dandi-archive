<template>
  <v-progress-linear
    v-if="!girderDandiset"
    indeterminate
  />
  <PublishFileBrowser
    v-else-if="version !== draftVersion"
    :identifier="identifier"
    :version="version"
  />
  <GirderFileBrowser
    v-else
    :identifier="identifier"
    :version="version"
  />
</template>

<script>
import { mapState, mapActions } from 'vuex';
import { draftVersion } from '@/utils';
import GirderFileBrowser from './GirderFileBrowser.vue';
import PublishFileBrowser from './PublishFileBrowser.vue';

export default {
  name: 'FileBrowser',
  components: {
    GirderFileBrowser,
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
    ...mapState('dandiset', ['publishDandiset', 'girderDandiset']),
  },
  async created() {
    // Don't extract girderDandiset or publishDandiset, for reactivity
    const { identifier, version } = this;

    if (!this.girderDandiset) {
      // Await so we can use this value afterwards
      await this.fetchGirderDandiset({ identifier });
    }

    if (!this.publishDandiset && version !== draftVersion) {
      this.fetchPublishDandiset({ identifier, version, girderId: this.girderDandiset._id });
    }
  },
  methods: {
    ...mapActions('dandiset', ['fetchPublishDandiset', 'fetchGirderDandiset']),
  },
};
</script>
