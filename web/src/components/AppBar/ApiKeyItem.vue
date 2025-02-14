<template>
  <v-list-item>
    <v-list-item-action class="mr-2">
      <!-- ".stop" prevents closing the parent v-menu when this is clicked -->
      <v-btn
        variant="text"
        @click.stop="refreshApiKey"
      >
        <v-icon>mdi-reload</v-icon>
      </v-btn>

      <CopyText
        :text="apiKey"
        label="API Key"
        icon-hover-text="Copy API key to clipboard"
      />
    </v-list-item-action>
  </v-list-item>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import CopyText from '@/components/CopyText.vue';
import { dandiRest } from '@/rest';

const apiKey = ref('');

async function fetchApiKey() {
  apiKey.value = await dandiRest.getApiKey();
}
async function refreshApiKey() {
  apiKey.value = await dandiRest.newApiKey();
}

// fetch API key when component is created
fetchApiKey();

</script>
