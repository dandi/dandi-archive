<template>
  <div>
    <v-toolbar
      color="grey darken-2 white--text"
    >
      <v-toolbar-title class="d-none d-md-block mx-8">
        My Dandisets
      </v-toolbar-title>
      <v-divider
        class="d-none d-md-block"
        vertical
      />
      <div class="mx-6">
        Sort By:
      </div>
      <v-chip-group
        v-model="selection"
        active-class="white light-blue--text"
        dark
        mandatory
      >
        <v-chip
          v-for="option in options"
          :key="option.name"
          @click="setSort(option.sort)"
        >
          {{ option.name }}
        </v-chip>
      </v-chip-group>
      <SearchField />
    </v-toolbar>
    <DandisetList
      class="
        mx-12
        my-12"
      :dandisets="dandisets"
    />
    <v-pagination
      v-model="page"
      :value="page"
      :length="pages"
      @input="reload"
    />
  </div>
</template>

<script>
import { mapState } from 'vuex';

import DandisetList from '@/components/DandisetList.vue';
import SearchField from '@/views/PublicDandisetsView/SearchField.vue';
import { basicDandisetSortingOptions } from '@/utils';

export default {
  name: 'MyDandisetsView',
  components: { DandisetList, SearchField },
  data() {
    return {
      selection: 'newest',
      options: basicDandisetSortingOptions,
    };
  },
  computed: {
    page: {
      get() {
        return this.$store.state.publicDandisets.page;
      },
      set(page) {
        this.$store.state.publicDandisets.page = page;
      },
    },
    ...mapState('myDandisets', ['dandisets', 'pages']),
  },
  created() {
    this.reload();
  },
  methods: {
    setSort(sort) {
      this.$store.dispatch('myDandisets/changeSearchSettings', { sort });
    },
    reload() {
      this.$store.dispatch('myDandisets/reload');
    },
  },
};
</script>
