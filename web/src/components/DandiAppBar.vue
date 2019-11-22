<template>
  <v-app-bar app color="primary">
    <v-toolbar-title>
      <v-tooltip open-delay="1000" bottom>
        <template #activator="{ on }">
          <img v-on="on" class="logo" alt="DANDI logo" height="48px" src="../assets/logo.svg" />
        </template>
        <span>{{ version }}</span>
      </v-tooltip>
    </v-toolbar-title>
    <v-spacer/>
    <girder-search @select="selectSearchResult" search-mode="dandi"
        :search-types="['item']" :hide-options-menu="true" placeholder="Type search query" >
      <template v-slot:searchresult="result">
        <v-list-item-action>
          <v-icon> {{ $vuetify.icons.values[result._modelType] }} </v-icon>
        </v-list-item-action>
        <v-list-item-content>
          <v-list-item-title>{{ result.name }}</v-list-item-title>
          <v-list-item-subtitle>
            {{ result.meta.institution + " " + result.meta.lab + " lab" }}
          </v-list-item-subtitle>
        </v-list-item-content>
      </template>
    </girder-search>
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
  computed: {
    ...mapGetters(['loggedIn']),
    version() {
      return process.env.VUE_APP_VERSION;
    },
  },
  methods: mapActions(['logout', 'selectSearchResult']),
};
</script>

<style scoped>
.logo {
  vertical-align: middle;
}
</style>
