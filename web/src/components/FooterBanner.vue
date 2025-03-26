<template>
  <v-banner color="grey darken-1 text-center" v-if="bannerText">
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
