<template>
  <v-container v-page-title="'Sign Up'">
    <h4>Register with Github</h4>
    <v-btn
      v-for="provider in oauthProviders"
      :key="provider.id"
      :dark="iconMap[provider.id].dark"
      :color="iconMap[provider.id].color"
      :href="provider.url"
      class="ml-0 mr-3"
    >
      <v-icon left="left">
        {{ $vuetify.icons.values[iconMap[provider.id].icon] }}
      </v-icon>
      {{ provider.name }}
    </v-btn>
  </v-container>
</template>

<script>
import { OauthTokenPrefix, OauthTokenSuffix } from '@girder/components/src/rest';
import girderRest, { loggedIn } from '@/rest';

// Copied from https://github.com/girder/girder_web_components Authentication/OAuth.vue
const iconMap = {
  github: { dark: true, icon: 'github' },
  google: { dark: true, icon: 'google', color: '#3367d6' },
  linkedin: { dark: true, icon: 'linkedin', color: '#283e4a' },
  bitbucket: { dark: false, icon: 'bitbucket' },
  box: { dark: true, icon: 'box_com', color: '#0071f7' },
  globus: { dark: true, icon: 'globus', color: '#335a95' },
};
export default {
  name: 'UserRegisterView',
  data() {
    return {
      iconMap,
    };
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
