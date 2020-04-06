<template>
  <v-container style="height: 100%;">
    <v-card flat>
      <v-card-title>Public Dandisets</v-card-title>
      <v-divider />
      <v-row>
        <v-col cols="12">
          <DandisetList :dandisets="dandisets"/>
        </v-col>
      </v-row>
    </v-card>
  </v-container>
</template>

<script>
import { mapState } from 'vuex';

import DandisetList from '@/components/DandisetList.vue';

export default {
  components: { DandisetList },
  data() {
    return {
      dandisets: [],
    };
  },
  computed: {
    ...mapState(['girderRest']),
  },
  async created() {
    const { data: dandisets } = await this.girderRest.get('dandi');
    this.dandisets = dandisets;
  },
  methods: {
    async fetchDandisets() {
      this.$store.girderRest.get('dandi');
    },
  },
};
</script>
<style>
.girder-file-browser .secondary .row .spacer {
  display: none;
}
</style>
