<template>
  <v-form
    style="width: 100%;"
    @submit="performSearch"
  >
    <v-text-field
      :model-value="$route.query.search"
      placeholder="Search Dandisets by name, description, identifier, or contributor name"
      variant="outlined"
      hide-details
      :density="dense ? 'compact' : undefined"
      bg-color="white"
      color="black"
      @update:model-value="updateSearch"
    >
      <template #prepend-inner>
        <v-icon @click="performSearch">
          mdi-magnify
        </v-icon>
      </template>
    </v-text-field>
  </v-form>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import type { RouteLocationRaw } from 'vue-router';
import { useRoute } from 'vue-router';
import router from '@/router';

defineProps({
  dense: {
    type: Boolean,
    required: false,
    default: true,
  },
});

const route = useRoute();
const currentSearch = ref(route.query.search || '');

function updateSearch(search: string) {
  currentSearch.value = search;
}

function performSearch(evt: Event) {
  evt.preventDefault(); // prevent form submission from refreshing page

  if (currentSearch.value === route.query.search) {
    // nothing has changed, do nothing
    return;
  }
  if (route.name !== 'searchDandisets') {
    router.push({
      name: 'searchDandisets',
      query: {
        search: currentSearch.value,
      },
    });
  } else {
    router.replace({
      ...route,
      query: {
        ...route.query,
        search: currentSearch.value,
      },
    } as RouteLocationRaw);
  }
}
</script>
