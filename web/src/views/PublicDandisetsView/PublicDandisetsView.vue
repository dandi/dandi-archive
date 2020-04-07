<template>
  <div>
    <v-toolbar
      color="grey darken-2 white--text"
    >
      <v-toolbar-title class="d-none d-md-block mx-8">
        Public Dandisets
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

const OPTIONS = [
  {
    name: 'Oldest',
    sort: {
      field: 'created',
      direction: 1,
    },
  },
  {
    name: 'Newest',
    sort: {
      field: 'created',
      direction: -1,
    },
  },
  {
    name: 'Name',
    sort: {
      field: 'meta.dandiset.name',
      direction: 1,
    },
  },
];

export default {
  name: 'PublicDandisetsView',
  components: { DandisetList, SearchField },
  data() {
    return {
      selection: 'newest',
      options: OPTIONS,
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
    ...mapState('publicDandisets', ['dandisets', 'pages']),
  },
  created() {
    this.reload();
  },
  methods: {
    setSort(sort) {
      this.$store.dispatch('publicDandisets/changeSearchSettings', { sort });
    },
    reload() {
      this.$store.dispatch('publicDandisets/reload');
    },
  },
};
</script>
