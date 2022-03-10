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
import { mapState, mapActions } from 'vuex';
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
    ...mapState('dandiset', ['publishDandiset']),
  },
  async created() {
    // Don't extract publishDandiset, for reactivity
    const { identifier, version } = this;
    if (!this.publishDandiset) {
      this.fetchPublishDandiset({ identifier, version });
    }
  },
  methods: {
    ...mapActions('dandiset', ['fetchPublishDandiset']),
  },
};
</script>
