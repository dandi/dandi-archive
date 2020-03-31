<template>
  <v-list-item>
    <v-list-item-action class="mr-2">
      <v-btn
        icon
        @click="reloadApiKey"
      >
        <v-icon>mdi-reload</v-icon>
      </v-btn>
    </v-list-item-action>
    <v-list-item-content>
      <v-text-field
        ref="apiKey"
        v-model="apiKey"
        label="Api Key"
        :readonly="true"
        append-outer-icon="mdi-content-copy"
        @click:append-outer="copyApiKey"
      />
    </v-list-item-content>
  </v-list-item>
</template>

<script>
import { mapActions, mapState } from 'vuex';

export default {
  name: 'ApiKeyItem',
  computed: {
    ...mapState('girder', ['apiKey']),
  },
  created() {
    this.fetchApiKey();
  },
  methods: {
    copyApiKey() {
      const { input: value } = this.$refs.apiKey.$refs;
      value.focus();
      document.execCommand('selectAll');
      value.select();
      document.execCommand('copy');
    },
    ...mapActions('girder', ['fetchApiKey', 'reloadApiKey']),
  },
};
</script>
