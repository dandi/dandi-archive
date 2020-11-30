<template>
  <!-- maybe...
    :close-on-content-click="false"
  -->
  <v-menu offset-y>
    <template #activator="{ on }">
      <v-btn
        icon
        v-on="on"
      >
        <v-avatar color="light-blue lighten-4">
          <span class="primary--text">
            {{ userInitials }}
          </span>
        </v-avatar>
      </v-btn>
    </template>
    <v-list dense>
      <ApiKeyItem />
      <v-list-item @click="logout">
        <v-list-item-content>
          Logout
        </v-list-item-content>
        <v-list-item-action>
          <v-icon>mdi-logout</v-icon>
        </v-list-item-action>
      </v-list-item>
    </v-list>
  </v-menu>
</template>

<script>
import { girderRest, publishRest, user } from '@/rest';
import ApiKeyItem from '@/components/AppBar/ApiKeyItem.vue';
import toggles from '@/featureToggle';

export default {
  name: 'UserMenu',
  components: {
    ApiKeyItem,
  },
  data() {
    return {
    };
  },
  computed: {
    user,
    userInitials() {
      if (this.user) {
        const { firstName, lastName } = this.user;
        if (firstName && lastName) {
          return (
            firstName.charAt(0).toLocaleUpperCase() + lastName.charAt(0).toLocaleUpperCase()
          );
        }

        const { login } = this.user;
        if (login) {
          return login.slice(0, 2);
        }
      }
      return '??';
    },
  },
  methods: {
    async logout() {
      if (toggles.DJANGO_API) {
        await publishRest.logout();
      } else {
        await girderRest.logout();
      }
    },
  },
};
</script>
