<template>
  <v-list-item>
    <v-list-item-action class="mr-2">
      <!-- ".stop" prevents closing the parent v-menu when this is clicked -->
      <v-btn
        icon
        @click.stop="refreshApiKey"
      >
        <v-icon>mdi-reload</v-icon>
      </v-btn>
    </v-list-item-action>
    <v-list-item-content>
      <CopyText
        :text="apiKey"
        label="API Key"
        icon-hover-text="Copy API key to clipboard"
      />
    </v-list-item-content>
  </v-list-item>
</template>

<script>
import CopyText from '@/components/CopyText.vue';
import { publishRest } from '@/rest';

export default {
  name: 'ApiKeyItem',
  components: {
    CopyText,
  },
  data() {
    return {
      apiKey: null,
    };
  },
  created() {
    this.fetchApiKey();
  },
  methods: {
    // gets the logged-in user's existing API key (and creates one if it doesn't exist)
    async fetchApiKey() {
      this.apiKey = await publishRest.getApiKey();
    },
    // gets a new API key for the logged-in user and deletes the old one
    async refreshApiKey() {
      this.apiKey = await publishRest.newApiKey();
    },
  },
};
</script>
