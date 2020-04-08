<template>
  <v-container style="height: 100%;">
    <v-card flat>
      <v-card-title>Public Dandisets</v-card-title>
      <v-progress-linear v-if="loading" indeterminate />
      <v-divider/>
      <v-row>
        <v-col cols="12">
          <DandisetList :dandisets="dandisets"/>
        </v-col>
      </v-row>
      <v-row>
        <v-pagination
          v-model="page"
          :length="length"
          @input="fetchDandisets"
        />
      </v-row>
    </v-card>
  </v-container>
</template>

<script>
import { mapState } from 'vuex';

import DandisetList from '@/components/DandisetList.vue';

const DANDISETS_PER_PAGE = 10;

export default {
  components: { DandisetList },
  data() {
    return {
      dandisets: [],
      page: 1,
      offset: 0,
      total: 0,
      loading: false,
    };
  },
  computed: {
    ...mapState(['girderRest']),
    length() {
      return Math.ceil(this.total / DANDISETS_PER_PAGE);
    },
  },
  async created() {
    this.fetchDandisets();
  },
  methods: {
    async fetchDandisets() {
      this.loading = true;

      const { data: { draft_count: draftCount } } = await this.girderRest.get('dandi/stats');
      const { data: dandisets } = await this.girderRest.get('dandi', {
        params: {
          limit: DANDISETS_PER_PAGE,
          offset: (this.page - 1) * DANDISETS_PER_PAGE,
        },
      });

      this.total = draftCount;
      this.dandisets = dandisets;

      this.loading = false;
    },
  },
};
</script>
<style>
.girder-file-browser .secondary .row .spacer {
  display: none;
}
</style>
