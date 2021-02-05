<template>
  <v-app class="dandi-app">
    <AppBar />
    <v-main>
      <router-view />
      <DandiFooter />
    </v-main>
  </v-app>
</template>

<script>
import AppBar from '@/components/AppBar/AppBar.vue';
import DandiFooter from '@/components/DandiFooter.vue';
import store from '@/store';
import toggles from '@/featureToggle';

export default {
  components: {
    AppBar,
    DandiFooter,
  },
  computed: {
    DJANGO_API() {
      return toggles.DJANGO_API;
    },
  },
  created() {
    this.$watch('DJANGO_API', () => {
      store.dispatch('dandiset/fetchSchema');
    }, { immediate: true });
  },
};
</script>

<style scoped>
.dandi-app {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>
