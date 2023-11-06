<template>
  <v-container
    class="grey darken-3 pa-0"
    fluid
  >
    <v-row class="py-6 mt-2">
      <template v-for="stat in stats">
        <v-col
          :key="stat.name"
          class="py-0 flex-grow-1"
          md="4"
          sm="4"
          cols="12"
        >
          <SingleStat
            :name="stat.name"
            :value="stat.value.toString()"
            :description="stat.description"
            :href="stat.href"
          />
        </v-col>
      </template>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import filesize from 'filesize';
import { dandiRest } from '@/rest';
import SingleStat from '@/views/HomeView/SingleStat.vue';

const dandisets = ref(0);
const users = ref(0);
const size = ref(0);

const stats = computed(() => [
  {
    name: 'dandisets',
    value: dandisets.value,
    description: 'A DANDI dataset including files and dataset-level metadata',
    href: '/dandiset',
  },
  { name: 'users', value: users.value },
  { name: 'total data size', value: filesize(size.value, { round: 0, base: 10, standard: 'iec' }) },
]);

// equivalent of async created method in options API
dandiRest.stats().then((data) => {
  dandisets.value = data.dandiset_count;
  users.value = data.user_count;
  size.value = data.size;
});
</script>
