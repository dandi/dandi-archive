<template>
  <v-app class="dandi-app">
    <dandi-app-bar />
    <v-content>
      <router-view />
      <DandiFooter />
    </v-content>
  </v-app>
</template>

<script>
import DandiAppBar from './components/DandiAppBar.vue';
import DandiFooter from './components/DandiFooter.vue';

export default {
  components: { DandiAppBar, DandiFooter },
};
</script>

<style>
.dandi-app {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>
