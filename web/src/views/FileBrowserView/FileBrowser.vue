<template>
  <v-progress-linear
    v-if="!girderDandiset && !publishDandiset"
    indeterminate
  />
  <PublishFileBrowser
    v-else-if="DJANGO_API"
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
import { draftVersion } from '@/utils/constants';
import toggles from '@/featureToggle';
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

    if (toggles.DJANGO_API) {
      if (!this.publishDandiset) {
        this.fetchPublishDandiset({ identifier, version });
      }
    } else if (!this.girderDandiset) {
      // Await so we can use this value afterwards
      await this.fetchGirderDandiset({ identifier });
    }
  },
  methods: {
    ...mapActions('dandiset', ['fetchPublishDandiset', 'fetchGirderDandiset']),
  },
};
</script>
