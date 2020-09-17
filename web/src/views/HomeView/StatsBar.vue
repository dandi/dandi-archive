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
          md="2"
          sm="4"
          cols="6"
        >
          <SingleStat
            :name="stat.name"
            :value="stat.value.toString()"
            :description="stat.description"
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
import { girderRest } from '@/rest';
import filesize from 'filesize';
import SingleStat from '@/views/HomeView/SingleStat.vue';

export default {
  name: 'StatsBar',
  components: { SingleStat },
  data() {
    return {
      dandisets: 0,
      users: 0,
      species: 0,
      subjects: 0,
      cells: 0,
      size: 0,
    };
  },
  computed: {
    stats() {
      return [
        { name: 'dandisets', value: this.dandisets, description: 'A DANDI dataset including files and dataset-level metadata' },
        { name: 'users', value: this.users },
        { name: 'species', value: this.species },
        { name: 'subjects', value: this.subjects },
        { name: 'cells', value: this.cells },
        { name: 'total data size', value: filesize(this.size, { round: 0 }) },
      ]
    },
  },
  async created() {
    const { data } = await girderRest.get('dandi/stats');
    this.dandisets = data.draft_count;
    this.users = data.user_count;
    this.species = data.species_count;
    this.subjects = data.subject_count;
    this.cells = data.cell_count;
    this.size = data.size;
  }
};
</script>
