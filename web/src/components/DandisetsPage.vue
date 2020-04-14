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
      sortField: sortingOptions[0].field,
      sortDir: 1,
      dandisets: [],
      pages: 0,
      page: Number(this.$route.query.page) || 1,
    };
  },
  computed: {
    listingUrl() {
      return this.user ? 'dandi/user' : 'dandi';
    },
  },
  watch: {
    page() {
      this.updateRouter();
      this.reload();
    },
  },
  created() {
    this.reload();
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
      this.reload();
    },
    updateRouter() {
      const { page } = this;
      this.$router.replace({
        ...this.$route,
        query: {
          page,
        },
      });
    },
    async reload() {
      const {
        listingUrl, page, sortField, sortDir,
      } = this;

      const { data: dandisets, headers } = await girderRest.get(listingUrl, {
        params: {
          limit: DANDISETS_PER_PAGE,
          offset: (page - 1) * DANDISETS_PER_PAGE,
          sort: sortField,
          sortdir: sortDir,
        },
      });
      const total = headers['girder-total-count'];

      this.dandisets = dandisets;
      this.pages = Math.ceil(total / DANDISETS_PER_PAGE);
    },
  },
};
</script>
