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
import filesize from 'filesize';
import { mapState } from 'vuex';
import SingleStat from '@/views/HomeView/SingleStat.vue';

export default {
  name: 'StatsBar',
  components: { SingleStat },
  computed: mapState({
    stats: (state) => [
      { name: 'dandisets', value: state.stats.drafts, description: 'Draft dandisets, that is. Publishing is coming soon™' },
      { name: 'users', value: state.stats.users },
      { name: 'species', value: state.stats.species },
      { name: 'subjects', value: state.stats.subjects },
      { name: 'cells', value: state.stats.cells },
      { name: 'total data size', value: filesize(state.stats.size, { round: 0 }) },
    ],
  }),
};
</script>
