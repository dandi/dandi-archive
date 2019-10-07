<template>
  <v-app class="dandi-app">
    <dandi-app-bar />
    <v-content>
      <v-container>
        <router-view/>
      </v-container>
    </v-content>
  </v-app>
</template>

<script>
import DandiAppBar from './components/DandiAppBar.vue';

export default {
  components: { DandiAppBar },
};
</script>

<style>
.dandi-app {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>
