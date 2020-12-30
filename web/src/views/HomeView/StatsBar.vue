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
          :md="(DJANGO_API) ? 4 : 2"
          :sm="(DJANGO_API) ? 4 : 4"
          :cols="(DJANGO_API) ? 12 : 6"
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
import { girderRest, publishRest } from '@/rest';
import filesize from 'filesize';
import SingleStat from '@/views/HomeView/SingleStat.vue';
import toggles from '@/featureToggle';

export default {
  name: 'StatsBar',
  components: { SingleStat },
  data() {
    return {
      dandisets: 0,
      users: 0,
      size: 0,
      // Girder only
      species: 0,
      subjects: 0,
      cells: 0,
    };
  },
  computed: {
    stats() {
      if (toggles.DJANGO_API) {
        return [
          { name: 'published dandisets', value: this.dandisets, description: 'A DANDI dataset including files and dataset-level metadata' },
          { name: 'users', value: this.users },
          { name: 'total data size', value: filesize(this.size, { round: 0 }) },
        ];
      }
      return [
        { name: 'dandisets', value: this.dandisets, description: 'A DANDI dataset including files and dataset-level metadata' },
        { name: 'users', value: this.users },
        { name: 'species', value: this.species },
        { name: 'subjects', value: this.subjects },
        { name: 'cells', value: this.cells },
        { name: 'total data size', value: filesize(this.size, { round: 0 }) },
      ];
    },
  },
  async created() {
    if (toggles.DJANGO_API) {
      const data = await publishRest.stats();
      this.dandisets = data.published_dandiset_count;
      this.users = data.user_count;
      this.size = data.size;
    } else {
      const { data } = await girderRest.get('dandi/stats');
      this.dandisets = data.draft_count;
      this.users = data.user_count;
      this.species = data.species_count;
      this.subjects = data.subject_count;
      this.cells = data.cell_count;
      this.size = data.size;
    }
  },
};
</script>
