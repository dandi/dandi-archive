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
    <v-list
      id="user-menu"
      dense
    >
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

<script lang="ts">
import { computed, defineComponent } from '@vue/composition-api';

import { publishRest, user as userFunc } from '@/rest';
import ApiKeyItem from '@/components/AppBar/ApiKeyItem.vue';

export default defineComponent({
  name: 'UserMenu',
  components: {
    ApiKeyItem,
  },
  setup() {
    const user = computed(userFunc);
    const userInitials = computed(() => {
      if (user.value) {
        const { name } = user.value;
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
      }
      return '??';
    });

    async function logout() {
      await publishRest.logout();
    }

    return {
      userInitials,
      logout,
    };
  },
});
</script>
