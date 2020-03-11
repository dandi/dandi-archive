<template>
  <v-app-bar app color="primary">
    <v-toolbar-title>
      <img align="center" alt="DANDI logo" height="48px" src="@/assets/logo.svg" />
    </v-toolbar-title>
    <v-tooltip bottom>
      <template v-slot:activator="{ on }">
        <v-btn text href="//www.dandiarchive.org"
        class="ml-2 white--text" dark v-on="on">About</v-btn>
      </template>
      <span>You are currently viewing the data portal.
      Click this button to learn more about the DANDI project.</span>
    </v-tooltip>
    <v-tooltip bottom>
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
          @click="reloadAPIKey"
        >
          <v-list-item-action class="mr-2">
            <v-btn icon>
              <v-icon>mdi-reload</v-icon>
            </v-btn>
          </v-list-item-action>
          <v-list-item-title>{{ apiKey }}</v-list-item-title>
        </v-list-item>
        <v-list-item
          @click="logout"
        >
          <v-list-item-action class="mr-2">
            <v-btn icon>
              <v-icon>$vuetify.icons.logout</v-icon>
            </v-btn>
          </v-list-item-action>
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
import { mapActions, mapGetters, mapState } from 'vuex';
import { Search as GirderSearch, Authentication as GirderAuth } from '@girder/components/src/components';

export default {
  components: { GirderSearch, GirderAuth },
  asyncComputed: {
    async apiKey() {
      const { status, data } = await this.girderRest.get(
        `api_key?userId=${this.user._id}&limit=50&sort=name&sortdir=1`,
      );
      if (status === 200 && data[0]) {
        // if there is an existing api key
        if (data[0]._modelType === 'api_key') {
          // set the user key
          this.user.key = data[0].key;
          return this.user.key;
        }
      } else {
        // create a key using "POST" endpoint
        const { status2, data2 } = await this.girderRest.post(
          '/api_key?name=dandicli&scope=%20%5B%22core.data.read%22%2C%20%20%22core.data.write%22%5D&tokenDuration=30&active=true',
        );
        if (status2 === 200) {
          this.user.key = data2.key;
          return this.user.key;
        }
      }
    },
  },
  computed: {
    ...mapGetters(['loggedIn', 'user']),
    ...mapState(['girderRest']),
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
  methods: {
    async reloadAPIKey() {
      const { status, data } = await this.girderRest.get(
        `/api_key?userId=${this.user._id}&limit=50&sort=name&sortdir=1`,
      );
      if (status === 200 && data[0]) {
        // send the key id to "PUT" endpoint for updating
        this.user.keyId = data[0]._id;
        const updated = await this.girderRest.put(`api_key/${this.user.keyId}`);
        this.user.key = updated.data.key;
        return this.user.key;
      }
    },
    ...mapActions(['logout', 'selectSearchResult']),
  },
};
</script>
