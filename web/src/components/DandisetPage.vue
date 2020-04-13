<template>
  <div>
    <v-toolbar
      color="grey darken-2 white--text"
    >
      <v-toolbar-title class="d-none d-md-block mx-8">
        {{ title }}
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
          @click="changeSort({sort: option.sort})"
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
      :length="pages"
    />
  </div>
</template>

<script>
import DandisetList from '@/components/DandisetList.vue';
import SearchField from '@/views/PublicDandisetsView/SearchField.vue';
import { basicDandisetSortingOptions } from '@/utils';

export default {
  name: 'DandisetPage',
  components: { DandisetList, SearchField },
  props: {
    title: {
      type: String,
      required: true,
    },
    module: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      selection: 'newest',
      options: basicDandisetSortingOptions,
    };
  },
  computed: {
    page: {
      get() {
        return this.moduleRoot.page;
      },
      set(page) {
        this.changePage({ page });
      },
    },
    moduleRoot() {
      return this.$store.state[this.module];
    },
    dandisets() {
      return this.moduleRoot.dandisets;
    },
    pages() {
      return this.moduleRoot.pages;
    },
  },
  created() {
    this.reload();
  },
  methods: {
    changeSort(payload) {
      return this.$store.dispatch(`${this.module}/changeSort`, payload);
    },
    changePage(payload) {
      return this.$store.dispatch(`${this.module}/changePage`, payload);
    },
    reload(payload) {
      return this.$store.dispatch(`${this.module}/reload`, payload);
    },
  },
};
</script>
