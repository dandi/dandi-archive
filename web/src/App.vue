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

<script lang="ts">
import { defineComponent, onMounted, ref } from 'vue';

import { dandiRest } from '@/rest';
import store from '@/store';
import AppBar from '@/components/AppBar/AppBar.vue';
import DandiFooter from '@/components/DandiFooter.vue';
import UserStatusBanner from '@/components/UserStatusBanner.vue';

const SERVER_DOWNTIME_MESSAGE = process.env.VUE_APP_SERVER_DOWNTIME_MESSAGE || 'Connection to server failed.';

export default defineComponent({
  components: {
    AppBar,
    DandiFooter,
    UserStatusBanner,
  },
  setup() {
    const verifiedServerConnection = ref(false);
    const connectedToServer = ref(true);

    onMounted(() => {
      Promise.all([
        store.dispatch.dandiset.fetchSchema(),
        dandiRest.restoreLogin(),
      ]).then(() => {
        connectedToServer.value = true;
      }).catch(() => {
        connectedToServer.value = false;
      }).finally(() => {
        verifiedServerConnection.value = true;
      });
    });

    return {
      connectedToServer,
      verifiedServerConnection,
      SERVER_DOWNTIME_MESSAGE,
    };
  },
});
</script>

<style scoped>
.dandi-app {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>
