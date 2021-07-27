<template>
  <v-container
    class="grey darken-3 pa-0"
    fluid
  >
    <v-row class="py-6">
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
        <!-- TODO dividers destroy the grid system breakpoints
        <v-divider
          :key="stat.name + '-divider'"
          vertical
          class="grey"
        />
        -->
      </template>
    </v-row>
  </v-container>
</template>

<script>
import { publishRest } from '@/rest';
import filesize from 'filesize';
import SingleStat from '@/views/HomeView/SingleStat.vue';

export default {
  name: 'StatsBar',
  components: { SingleStat },
  data() {
    return {
      dandisets: 0,
      users: 0,
      size: 0,
    };
  },
  computed: {
    stats() {
      return [
        {
          name: 'dandisets',
          value: this.dandisets,
          description: 'A DANDI dataset including files and dataset-level metadata',
          href: '/#/dandiset',
        },
        { name: 'users', value: this.users },
        { name: 'total data size', value: filesize(this.size, { round: 0, base: 10, standard: 'iec' }) },
      ];
    },
  },
  async created() {
    const data = await publishRest.stats();
    this.dandisets = data.dandiset_count;
    this.users = data.user_count;
    this.size = data.size;
  },
};
</script>
