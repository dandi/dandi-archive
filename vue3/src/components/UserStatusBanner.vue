<template>
  <v-banner
    v-if="bannerInfo"
    single-line
    :color="bannerInfo.color"
  >
    <template #icon>
      <v-icon size="36">
        {{ bannerInfo.icon }}
      </v-icon>
    </template>
    {{ bannerInfo.text }}
  </v-banner>
</template>

<script lang="ts">
import { user } from '@/rest';
import type { ComputedRef } from 'vue';
import { computed, defineComponent } from 'vue';

interface StatusBanner {
  text: string,
  icon: string,
  color: string,
}

export default defineComponent({
  name: 'UserStatusBanner',
  components: { },
  setup() {
    const bannerInfo: ComputedRef<StatusBanner|null> = computed(() => {
      switch (user.value?.status) {
        case 'PENDING':
          return {
            text: 'Your DANDI account is currently pending approval. Please allow up to 2 business days for approval and contact the DANDI admins at help@dandiarchive.org if you have any questions.',
            icon: 'mdi-timer-sand-empty',
            color: 'warning',
          };
        case 'REJECTED':
          return {
            text: 'Your DANDI account was denied approval. Please contact the DANDI admin team at help@dandiarchive.org if you would like to appeal this decision.',
            icon: 'mdi-close-octagon',
            color: 'error',
          };
        default:
          return null;
      }
    });

    return {
      bannerInfo,
    };
  },
});
</script>
