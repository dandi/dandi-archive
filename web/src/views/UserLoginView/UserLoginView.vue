<template>
  <v-container v-page-title="'Log In'">
    <GirderAuth
      :force-otp="false"
      :show-forgot-password="false"
      :oauth="true"
    />
  </v-container>
</template>

<script>
import { Authentication as GirderAuth } from '@girder/components/src/components';
import { loggedIn } from '@/rest';

export default {
  name: 'UserLoginView',
  components: {
    GirderAuth,
  },
  computed: {
    loggedIn,
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
