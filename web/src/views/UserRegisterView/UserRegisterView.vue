<template>
  <v-container>
    <GirderRegister :oauth-providers="oauthProviders" />
  </v-container>
</template>

<script>
import GirderRegister from '@girder/components/src/components/Authentication/Register.vue';
import { OauthTokenPrefix, OauthTokenSuffix } from '@girder/components/src/rest';
import girderRest, { loggedIn } from '@/rest';

export default {
  name: 'UserRegisterView',
  components: {
    GirderRegister,
  },
  computed: {
    loggedIn,
  },
  asyncComputed: {
    async oauthProviders() {
      const { data } = await girderRest.get('oauth/provider', {
        params: {
          redirect: `${window.location.href}${OauthTokenPrefix}{girderToken}${OauthTokenSuffix}`,
          list: true,
        },
      });
      return data;
    },
  },
  watch: {
    loggedIn(val) {
      if (val) {
        this.$router.push({ name: 'home' });
      }
    },
  },
};
</script>
