<template>
  <v-app-bar
    app
    color="primary"
  >
    <router-link to="/root">
      <v-toolbar-title>
        <img
          align="center"
          alt="DANDI logo"
          height="48px"
          src="@/assets/logo.svg"
        >
      </v-toolbar-title>
    </router-link>
    <v-tooltip bottom>
      <template v-slot:activator="{ on }">
        <v-btn
          text
          :href="dandiUrl"
          class="ml-2 white--text"
          dark
          v-on="on"
        >
          About
        </v-btn>
      </template>
      <span>You are currently viewing the data portal.
        Click this button to learn more about the DANDI project.</span>
    </v-tooltip>
    <v-dialog
      v-model="regdialog"
      max-width="600px"
    >
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
            v-model="name"
            label="Name*"
            hint="Provide a title for this dataset"
            persistent-hint
            :counter="120"
            required
          />
          <v-textarea
            v-model="description"
            label="Description*"
            hint="Provide a description for this dataset"
            :counter="3000"
            persistent-hint
            required
          />
          <small>*indicates required field</small>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
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
        <v-chip
          class="ml-2"
          color="secondary"
          v-on="on"
        >
          <v-icon
            left
            color="amber"
          >
            $vuetify.icons.alert
          </v-icon>Early Access
        </v-chip>
      </template>
      <span>
        DANDI is currently running in limited access mode.
        Public release isn't until March 2020.
      </span>
    </v-tooltip>
    <v-spacer />
    <girder-search
      search-mode="dandi"
      :search-types="['item']"
      :hide-options-menu="true"
      placeholder="Type search query"
      @select="selectSearchResult"
    >
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
    <v-menu
      v-if="loggedIn"
      offset-y
      :close-on-content-click="false"
    >
      <template v-slot:activator="{ on }">
        <v-btn
          class="ml-2"
          icon
          dark
          v-on="on"
        >
          <v-avatar color="primary darken-1">
            {{ initials }}
          </v-avatar>
        </v-btn>
      </template>
      <v-list dense>
        <v-list-item>
          <v-list-item-action class="mr-2">
            <v-btn
              icon
              @click="reloadApiKey"
            >
              <v-icon>mdi-reload</v-icon>
            </v-btn>
          </v-list-item-action>
          <v-list-item-content>
            <v-text-field
              ref="apiKey"
              v-model="apiKey"
              label="Api Key"
              :readonly="true"
              append-outer-icon="mdi-content-copy"
              @click:append-outer="copyApiKey"
            />
          </v-list-item-content>
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
    <v-dialog
      v-else
      max-width="600"
    >
      <template v-slot:activator="{ on }">
        <v-btn
          class="ml-4"
          v-on="on"
        >
          Login
        </v-btn>
      </template>
      <girder-auth
        :force-otp="false"
        :show-forgot-password="false"
        :oauth="true"
      />
    </v-dialog>
  </v-app-bar>
</template>

<script>
import { mapActions, mapState } from 'vuex';
import { Search as GirderSearch, Authentication as GirderAuth } from '@girder/components/src/components';

import { dandiUrl } from '@/utils';
import girderRest, { loggedIn, user } from '@/rest';

export default {
  components: { GirderSearch, GirderAuth },
  data: () => ({
    dandiUrl,
    name: '',
    description: '',
    regdialog: false,
  }),
  computed: {
    loggedIn,
    user,
    saveDisabled() {
      return !(this.name && this.description);
    },
    ...mapState('girder', ['apiKey']),
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
    copyApiKey() {
      const { input: value } = this.$refs.apiKey.$refs;
      value.focus();
      document.execCommand('selectAll');
      value.select();
      document.execCommand('copy');
    },
    async register_dandiset() {
      const { name, description } = this;
      const { status, data } = await girderRest.post('dandi', null, { params: { name, description } });

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
    ...mapActions('girder', ['logout', 'selectSearchResult', 'fetchApiKey', 'reloadApiKey']),
  },
};
</script>
