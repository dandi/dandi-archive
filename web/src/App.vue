<template>
  <v-app class="dandi-app">
    <AppBar />
    <v-content>
      <router-view />
      <DandiFooter />
    </v-content>
  </v-app>
</template>

<script>
import AppBar from '@/components/AppBar/AppBar.vue';
import DandiFooter from '@/components/DandiFooter.vue';

export default {
  components: {
    AppBar,
    DandiFooter,
  },
};
</script>

<style scoped>
.dandi-app {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>
