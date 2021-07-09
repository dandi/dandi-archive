<template>
  <v-container v-page-title="'Log In'">
    <p>
      TODO: Implement OAuth
    </p>
    <p>
      For now, you can "log in" to a Django account with a username/password
      using this console command:
      <code>
        setTokenHack('django_auth_token_for_user')
      </code>
    </p>
    <p>
      You can create a bookmark with this URL to make this quicker:
      <code>
        javascript:setTokenHack('django_auth_token_for_user')
      </code>
    </p>
  </v-container>
</template>

<script>
import { loggedIn } from '@/rest';

export default {
  name: 'UserLoginView',
  computed: {
    loggedIn,
    returnTo() {
      const { returnTo } = this.$route.query;
      return returnTo ? JSON.parse(returnTo) : { name: 'home' };
    },
  },
  watch: {
    loggedIn: {
      immediate: true,
      handler(val) {
        if (val) {
          this.$router.replace(this.returnTo);
        }
      },
    },
  },
};
</script>
