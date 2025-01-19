<template>
  <!-- maybe...
    :close-on-content-click="false"
  -->
  <v-menu>
    <template #activator="{ props }">
      <v-btn
        icon
        v-bind="props"
      >
        <v-avatar color="light-blue-lighten-4">
          <span class="text-primary">
            {{ userInitials }}
          </span>
        </v-avatar>
      </v-btn>
    </template>
    <v-list
      id="user-menu"
      density="compact"
    >
      <v-list-item>
        <span v-if="user">
          You are logged in as <a
            :href="`https://github.com/${user.username}`"
            target="_blank"
            rel="noopener"
            v-text="user.username"
          />.
        </span>
      </v-list-item>
      <ApiKeyItem v-if="user?.approved" />
      <v-list-item @click="logout">
        Logout
        <v-list-item-action>
          <v-icon>mdi-logout</v-icon>
        </v-list-item-action>
      </v-list-item>
    </v-list>
  </v-menu>
</template>

<script setup lang="ts">
import { computed } from 'vue';

import { user, dandiRest } from '@/rest';
import ApiKeyItem from '@/components/AppBar/ApiKeyItem.vue';

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
