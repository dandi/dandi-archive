<template>
  <v-app-bar app color="primary">
    <v-toolbar-title>
      <img class="logo" alt="DANDI logo" height="48px" src="../assets/logo.svg" />
    </v-toolbar-title>
    <v-spacer/>
    <girder-search @select="selectSearchResult" search-mode="dandi"
        :search-types="['item']" :hide-options-menu="true" placeholder="Type search query" />
    <v-btn v-if="loggedIn" icon dark @click="logout">
      <v-icon>$vuetify.icons.logout</v-icon>
    </v-btn>
  </v-app-bar>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';
import { Search as GirderSearch } from '@girder/components/src/components';

export default {
  components: { GirderSearch },
  computed: mapGetters(['loggedIn']),
  methods: mapActions(['logout', 'selectSearchResult']),
};
</script>

<style scoped>
.logo {
  vertical-align: middle;
}
</style>
