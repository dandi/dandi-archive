<template>
  <v-app-bar app color="primary">
    <v-toolbar-title>
      <img align="center" alt="DANDI logo" height="48px" src="@/assets/logo.svg" />
    </v-toolbar-title>
    <v-tooltip right>
      <template v-slot:activator="{ on }">
        <v-chip class="ml-2" color="secondary" v-on="on">
          <v-icon left color="amber">$vuetify.icons.alert</v-icon>Early Access
        </v-chip>
      </template>
      <span>
        DANDI is currently running in limited access mode.
        Public release isn't until March 2020.
      </span>
    </v-tooltip>
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
      <template v-slot:noresult="{ searchText }">
        <v-list-item-action>
          <v-icon>$vuetify.icons.alert</v-icon>
        </v-list-item-action>
        <v-list-item-content>
          <v-list-item-title>
            No results found for query '{{ searchText }}'
          </v-list-item-title>
          <v-list-item-subtitle>
            Please use our search grammar.
          </v-list-item-subtitle>
        </v-list-item-content>
      </template>
    </girder-search>
    <v-menu offset-y v-if="loggedIn">
      <template v-slot:activator="{ on }">
        <v-btn v-on="on" class="ml-2" icon dark>
          <v-avatar color="primary darken-1">
            {{ initials }}
          </v-avatar>
        </v-btn>
      </template>
      <v-list dense>
        <v-list-item
          @click="logout"
        >
          <v-list-item-icon class="mr-2">
            <v-icon>$vuetify.icons.logout</v-icon>
          </v-list-item-icon>
          <v-list-item-title>Logout</v-list-item-title>
        </v-list-item>
      </v-list>
    </v-menu>
    <v-dialog v-else max-width="600">
      <template v-slot:activator="{ on }">
        <v-btn v-on="on" class="ml-4">
          Login
        </v-btn>
      </template>
      <girder-auth :force-otp="false" :show-forgot-password="false" :oauth="true" />
    </v-dialog>
  </v-app-bar>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';
import { Search as GirderSearch, Authentication as GirderAuth } from '@girder/components/src/components';

export default {
  components: { GirderSearch, GirderAuth },
  computed: {
    ...mapGetters(['loggedIn', 'user']),
    version() {
      return process.env.VUE_APP_VERSION;
    },
    initials() {
      const first = this.user.firstName;
      const last = this.user.lastName;
      if (first && last) {
        return (
          first.charAt(0).toLocaleUpperCase() + last.charAt(0).toLocaleUpperCase()
        );
      }
      if (this.user.login) {
        return this.user.login.slice(0, 2);
      }
      return 'NA';
    },
  },
  methods: mapActions(['logout', 'selectSearchResult']),
};
</script>
