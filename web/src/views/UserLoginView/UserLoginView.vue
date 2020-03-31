<template>
  <v-container>
    TODO: UserLoginView
    <GirderAuth
      :force-otp="false"
      :show-forgot-password="false"
      :oauth="true"
    />
  </v-container>
</template>

<script>
import { Authentication as GirderAuth } from '@girder/components/src/components';

export default {
  name: 'UserLoginView',
  components: {
    GirderAuth,
  },
};
</script>
