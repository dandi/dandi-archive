<template>
  <v-app-bar app color="primary">
    <v-toolbar-title>
      <img align="center" alt="DANDI logo" height="48px" src="@/assets/logo.svg" />
    </v-toolbar-title>
    <v-tooltip bottom>
      <template v-slot:activator="{ on }">
        <v-btn text :href="dandiUrl"
        class="ml-2 white--text" dark v-on="on">About</v-btn>
      </template>
      <span>You are currently viewing the data portal.
      Click this button to learn more about the DANDI project.</span>
    </v-tooltip>
    <v-dialog max-width="600px" v-model="regdialog">
      <template v-slot:activator="{ on }">
        <v-btn
          text
          :disabled="!loggedIn"
          class="ml-2 white--text"
          dark
          v-on="on"
        >
          Register
        </v-btn>
      </template>
      <v-card>
        <v-card-title>
          <span class="headline">Register a new dataset</span>
        </v-card-title>
        <v-card-text>
          <v-text-field
            label="Name*"
            hint="Provide a title for this dataset"
            persistent-hint
            :counter="120"
            v-model="name"
            required
          />
          <v-textarea
            label="Description*"
            hint="Provide a description for this dataset"
            :counter="3000"
            persistent-hint
            v-model="description"
            required
          />
          <small>*indicates required field</small>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn
            type="submit"
            color="primary"
            :disabled="saveDisabled"
            @click="register_dandiset"
          >
            Register dataset
            <template v-slot:loader>
              <span>Registering...</span>
            </template>
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
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
          @click="reloadApiKey"
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

import { dandiUrl } from '@/utils';

export default {
  data: () => ({
    dandiUrl,
    name: '',
    description: '',
    regdialog: false,
  }),
  components: { GirderSearch, GirderAuth },
  computed: {
    saveDisabled() {
      return !(this.name && this.description);
    },
    ...mapGetters(['loggedIn', 'user']),
    ...mapState(['apiKey', 'girderRest']),
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
  created() {
    this.fetchApiKey();
  },
  methods: {
    async register_dandiset() {
      const { name, description } = this;
      const { status, data } = await this.girderRest.post('dandi', null, { params: { name, description } });

      if (status === 200) {
        this.name = '';
        this.description = '';
        this.$router.push({
          name: 'dandiset-metadata-viewer',
          params: { id: data._id },
        });
        this.regdialog = false;
      }
    },
    ...mapActions(['logout', 'selectSearchResult', 'fetchApiKey', 'reloadApiKey']),
  },
};
</script>
