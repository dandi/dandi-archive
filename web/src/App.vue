<template>
  <v-app
    v-if="verifiedServerConnection"
    class="dandi-app"
  >
    <AppBar />
    <v-main v-if="connectedToServer">
      <UserStatusBanner />
      <router-view />
      <DandiFooter />
    </v-main>

    <v-main
      v-else
      class="d-flex align-center text-center"
    >
      {{ SERVER_DOWNTIME_MESSAGE }}
    </v-main>
    <v-snackbar
      :model-value="showError"
      :timeout="-1"
      location="top right"
      color="error"
    >
      <span>
        Sorry, something went wrong on our side (the developers have been notified).
        Please try that operation again later.
      </span>
      <template #actions>
        <v-btn
          color="white"
          variant="text"
          @click="showError = false"
        >
          Close
        </v-btn>
      </template>
    </v-snackbar>
  </v-app>
</template>

<script setup lang="ts">
import { getCurrentInstance, onMounted, ref, watchEffect } from 'vue';

import { dandiRest } from '@/rest';
import { useDandisetStore } from '@/stores/dandiset';
import AppBar from '@/components/AppBar/AppBar.vue';
import DandiFooter from '@/components/DandiFooter.vue';
import UserStatusBanner from '@/components/UserStatusBanner.vue';

const store = useDandisetStore();

const SERVER_DOWNTIME_MESSAGE = import.meta.env.VITE_APP_SERVER_DOWNTIME_MESSAGE || 'Connection to server failed.';

const verifiedServerConnection = ref(false);
const connectedToServer = ref(true);

// Catch any unhandled errors and display a snackbar prompt notifying the user.
const showError = ref(false);
watchEffect(() => {
  // The `app` object isn't immediately available, so we need to wait
  // until the component is mounted to attach the error handler.
  const app = getCurrentInstance();
  if (app) {
    app.appContext.config.errorHandler = (err) => {
      showError.value = true;
      throw err;
    };
  }
});


onMounted(() => {
  Promise.all([
    store.fetchSchema(),
    dandiRest.restoreLogin(),
  ]).then(() => {
    connectedToServer.value = true;
  }).catch(() => {
    connectedToServer.value = false;
  }).finally(() => {
    verifiedServerConnection.value = true;
  });
});
</script>

<style scoped>
.dandi-app {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>
