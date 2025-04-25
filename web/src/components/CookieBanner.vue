<script setup lang="ts">
import { computed, ref } from 'vue';
import {
  cookiesEnabled as cookiesEnabledFunc
} from '@/rest';

const COOKIE_NAME = 'dandi-cookie-consent';

const dandiCookie = computed({
  get() {
    return document.cookie
      .split('; ')
      .find((row) => row.startsWith(`${COOKIE_NAME}=`))
      ?.split('=')[1] || null;
  },
  set(value: string) {
    // Set the cookie to expire in 6 months
    document.cookie = `${COOKIE_NAME}=${value}; path=/; max-age=15778476`;
  },
});

const open = ref(dandiCookie.value !== 'true');

const cookiesEnabled = computed(cookiesEnabledFunc);

function setCookie() {
  dandiCookie.value = 'true';
  open.value = false;
}
</script>

<template>
  <Transition
    class="position-fixed bottom-0 w-100 d-flex justify-center"
    appear
    :enter-from-class="'enter-from'"
    :enter-active-class="'enter-active'"
    :enter-to-class="'enter-to'"
    :leave-from-class="'leave-from'"
    :leave-active-class="'leave-active'"
    :leave-to-class="'leave-to'"
  >
    <v-card
      v-if="open"
      :key="`cookie-${open}`"
      color="secondary"
      class="pa-5 d-flex justify-space-between align-center"
      max-width="60%"
      style="left: 50%; transform: translateX(-50%); z-index: 1;"
    >
      <span v-if="cookiesEnabled">We use cookies to ensure you get the best experience on DANDI.</span>
      <span v-else>We noticed you're blocking cookies - note that certain aspects of the site may not work.</span>
      <v-btn
        class="bg-error"
        elevation="0"
        @click="setCookie"
      >
        Got it!
      </v-btn>
    </v-card>
  </Transition>
</template>

<style scoped>
  .enter-from, .leave-to {
    transform: translateY(12.5em);
    opacity: 0;
  }

  .enter-to, .leave-from {
    transform: translateY(0);
    opacity: 1;
  }

  .enter-active,
  .leave-active {
    transition: transform 0.4s ease-in, opacity 0.4s ease-in;
  }
</style>
