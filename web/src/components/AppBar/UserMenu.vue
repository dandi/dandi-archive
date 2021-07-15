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
    <v-list id="user-menu" dense>
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
import { publishRest, user } from '@/rest';
import ApiKeyItem from '@/components/AppBar/ApiKeyItem.vue';

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
        // TODO Girder uses camelCase. Delete after Girder is deprecated.
        const { firstName, lastName } = this.user;
        if (firstName && lastName) {
          return (
            firstName.charAt(0).toLocaleUpperCase() + lastName.charAt(0).toLocaleUpperCase()
          );
        }
        const { name } = this.user;
        if (name) {
          const name_parts = name.split(' ');
          if (name_parts.length >= 2) {
            const first_name = name_parts[0];
            const last_name = name_parts[name_parts.length - 1];
            return (
              first_name.charAt(0).toLocaleUpperCase() + last_name.charAt(0).toLocaleUpperCase()
            );
          }
        }
        // If first name + last name aren't specified, try to use the login instead
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
      await publishRest.logout();
    },
  },
};
</script>
