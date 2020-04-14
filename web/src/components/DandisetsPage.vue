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
        active-class="white light-blue--text"
        dark
        mandatory
      >
        <v-chip
          v-for="option in sortingOptions"
          :key="option.name"
          @click="changeSort(option)"
        >
          {{ option.name }}
          <v-icon right>
            <template v-if="sortDir === 1 || sortField !== option.field">
              mdi-sort-ascending
            </template>
            <template v-else>
              mdi-sort-descending
            </template>
          </v-icon>
        </v-chip>
      </v-chip-group>
      <SearchField />
    </v-toolbar>
    <DandisetList
      class="
        mx-12
        my-12"
      :dandisets="dandisets || []"
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
import girderRest from '@/rest';

const DANDISETS_PER_PAGE = 8;

const sortingOptions = [
  {
    name: 'Created',
    field: 'created',
  },
  {
    name: 'Name',
    field: 'meta.dandiset.name',
  },
];

export default {
  name: 'DandisetsPage',
  components: { DandisetList, SearchField },
  props: {
    title: {
      type: String,
      required: true,
    },
    user: {
      type: Boolean,
      required: false,
      default: false,
    },
  },
  data() {
    return {
      sortingOptions,
      sortField: this.$route.query.sortField || sortingOptions[0].field,
      sortDir: this.$route.query.sortDir || 1,
      page: Number(this.$route.query.page) || 1,
      total: 0,
    };
  },
  computed: {
    listingUrl() {
      return this.user ? 'dandi/user' : 'dandi';
    },
    pages() {
      return Math.ceil(this.total / DANDISETS_PER_PAGE) || 1;
    },
    route() {
      const {
        page, sortField, sortDir, $route,
      } = this;

      return {
        ...$route,
        query: {
          page,
          sortField,
          sortDir,
        },
      };
    },
  },
  asyncComputed: {
    async dandisets() {
      const {
        listingUrl, page, sortField, sortDir,
      } = this;

      const { data: dandisets } = await girderRest.get(listingUrl, {
        params: {
          limit: DANDISETS_PER_PAGE,
          offset: (page - 1) * DANDISETS_PER_PAGE,
          sort: sortField,
          sortdir: sortDir,
        },
      });

      return dandisets;
    },
  },
  watch: {
    route() {
      this.$router.replace(this.route);
    },
  },
  created() {
    this.getTotalDandisets();
  },
  methods: {
    changeSort(sort) {
      if (this.sortField === sort.field) {
        this.sortDir *= -1;
      } else {
        this.sortField = sort.field;
        this.sortDir = 1;
      }

      this.page = 1;
    },
    async getTotalDandisets() {
      const { headers: { 'girder-total-count': total } } = await girderRest.get(this.listingUrl, { params: { limit: 1 } });
      this.total = total;
    },
  },
};
</script>
