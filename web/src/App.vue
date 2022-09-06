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
  </v-app>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';

import { dandiRest } from '@/rest';
import { useDandisetStore } from '@/stores/dandiset';
import AppBar from '@/components/AppBar/AppBar.vue';
import DandiFooter from '@/components/DandiFooter.vue';
import UserStatusBanner from '@/components/UserStatusBanner.vue';

const store = useDandisetStore();

const SERVER_DOWNTIME_MESSAGE = process.env.VUE_APP_SERVER_DOWNTIME_MESSAGE || 'Connection to server failed.';

const verifiedServerConnection = ref(false);
const connectedToServer = ref(true);

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
