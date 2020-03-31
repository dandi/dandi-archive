<template>
  <v-app-bar
    app
  >
    <v-toolbar-title>
      <v-img
        alt="DANDI logo"
        contain
        max-height="48px"
        max-width="120px"
        src="@/assets/logo.svg"
      />
    </v-toolbar-title>

    <v-btn
      :to="{ name: 'home' }"
      exact
      text
    >
      Welcome
    </v-btn>
    <v-btn
      :to="{ name: 'publicDandisets' }"
      exact
      text
    >
      Public Dandisets
    </v-btn>
    <v-btn
      v-if="loggedIn"
      :to="{ name: 'myDandisets' }"
      exact
      text
    >
      My Dandisets
    </v-btn>
    <v-btn
      :href="dandiUrl"
      target="_blank"
      rel="noopener"
      text
    >
      About
      <v-icon>mdi-open-in-new</v-icon>
    </v-btn>

    <v-spacer />

    <span
      v-if="!loggedIn"
    >
      Want to create your own datasets?
    </span>
    <v-btn
      v-if="!loggedIn"
      :to="{ name: 'userRegister' }"
      color="primary"
      outlined
      rounded
    >
      Create Account
    </v-btn>
    <v-btn
      v-if="!loggedIn"
      :to="{ name: 'userLogin' }"
      color="primary"
      rounded
    >
      Login
    </v-btn>
    <UserMenu
      v-if="loggedIn"
    />
  </v-app-bar>
</template>

<script>
import { loggedIn } from '@/rest';
import { dandiUrl } from '@/utils';
import UserMenu from '@/components/AppBar/UserMenu.vue';

export default {
  name: 'AppBar',
  components: {
    UserMenu,
  },
  data() {
    return {
      dandiUrl,
    };
  },
  computed: {
    loggedIn,
  },
};
</script>
