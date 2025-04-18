<template>
  <v-banner
    v-if="bannerText"
    bg-color="grey-lighten-6"
    sticky
    :style="{ top: '64px' }"
  >
    <v-icon>
      mdi-information
    </v-icon>
    <span>
      {{ bannerText }}
    </span>
  </v-banner>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const bannerText = computed(() => import.meta.env.VITE_APP_FOOTER_BANNER_TEXT);
</script>
