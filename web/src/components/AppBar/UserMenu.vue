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
      <v-list-item>
        <v-list-item-content>
          <span v-if="dandiRest.user">
            You are logged in as <a
              :href="`https://github.com/${dandiRest.user.username}`"
              target="_blank"
              rel="noopener"
              v-text="dandiRest.user.username"
            />.
          </span>
        </v-list-item-content>
      </v-list-item>
      <ApiKeyItem v-if="dandiRest.user?.approved" />
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

<script setup lang="ts">
import { computed } from 'vue';

import { user as userFunc, dandiRest } from '@/rest';
import ApiKeyItem from '@/components/AppBar/ApiKeyItem.vue';

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
  await dandiRest.logout();
}

</script>
