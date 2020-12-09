<template>
  <div v-page-title="pageTitle">
    <v-toolbar color="grey darken-2 white--text">
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
        :value="sortOption"
        active-class="white light-blue--text"
        dark
        mandatory
      >
        <v-chip
          v-for="(option, i) in sortingOptions"
          :key="option.name"
          @click="changeSort(i)"
        >
          {{ option.name }}
          <v-icon right>
            <template v-if="sortDir === 1 || sortOption !== i">
              mdi-sort-ascending
            </template>
            <template v-else>
              mdi-sort-descending
            </template>
          </v-icon>
        </v-chip>
      </v-chip-group>
      <DandisetSearchField class="flex-grow-1" />
    </v-toolbar>
    <DandisetList
      v-if="dandisets && dandisets.length"
      class="mx-12 my-12"
      :dandisets="dandisets"
    />
    <v-container v-else>
      <v-row
        class="text-center ma-12 grey--text"
        align="center"
        justify="center"
      >
        <v-col>
          <v-progress-circular
            v-if="!dandisets"
            indeterminate
          />
          <slot
            v-else
            name="no-content"
          />
        </v-col>
      </v-row>
    </v-container>
    <v-pagination
      v-model="page"
      :length="pages"
    />
  </div>
</template>

<script>
import DandisetList from '@/components/DandisetList.vue';
import DandisetSearchField from '@/components/DandisetSearchField.vue';
import toggles from '@/featureToggle';
import { girderRest, publishRest } from '@/rest';

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
  components: { DandisetList, DandisetSearchField },
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
    search: {
      type: Boolean,
      required: false,
      default: false,
    },
  },
  data() {
    return {
      sortingOptions,
      sortOption: Number(this.$route.query.sortOption) || 0,
      sortDir: this.$route.query.sortDir || 1,
      page: Number(this.$route.query.page) || 1,
    };
  },
  computed: {
    pageTitle() {
      return (this.search) ? this.$route.query.search : this.title;
    },
    listingUrl() {
      if (this.user) {
        return 'dandi/user';
      }
      if (this.search) {
        return 'dandi/search';
      }
      return 'dandi';
    },
    pages() {
      return Math.ceil(this.totalDandisets / DANDISETS_PER_PAGE) || 1;
    },
    sortField() {
      return this.sortingOptions[this.sortOption].field;
    },
    queryParams() {
      const {
        page, sortOption, sortDir,
      } = this;
      return { page, sortOption, sortDir };
    },
    dandisets() {
      if (toggles.DJANGO_API) {
        return this.mostRecentDandisetVersions || [];
      }
      return this.girderDandisetRequest?.data || [];
    },
    totalDandisets() {
      if (toggles.DJANGO_API) {
        return this.djangoDandisetRequest ? this.djangoDandisetRequest.data.count : 0;
      }
      return this.girderDandisetRequest ? this.girderDandisetRequest.headers['girder-total-count'] : 0;
    },
  },
  asyncComputed: {
    async girderDandisetRequest() {
      if (toggles.DJANGO_API) {
        return null;
      }
      const {
        listingUrl, page, sortField, sortDir,
        $route: {
          query: {
            search,
          },
        },
      } = this;

      const {
        data, headers, status, statusText,
      } = await girderRest.get(listingUrl, {
        params: {
          limit: DANDISETS_PER_PAGE,
          offset: (page - 1) * DANDISETS_PER_PAGE,
          sort: sortField,
          sortdir: sortDir,
          search,
        },
      });

      return {
        data, headers, status, statusText,
      };
    },
    async djangoDandisetRequest() {
      if (!toggles.DJANGO_API) {
        return null;
      }
      return publishRest.dandisets({ page: this.page, page_size: DANDISETS_PER_PAGE });
    },
    async mostRecentDandisetVersions() {
      if (this.djangoDandisetRequest === null) {
        return null;
      }
      return Promise.all(this.djangoDandisetRequest.data.results.map(
        (dandiset) => publishRest.mostRecentVersion(dandiset.identifier),
      ));
    },
  },
  watch: {
    queryParams(params) {
      this.$router.replace({
        ...this.$route,
        query: {
          // do not override the search parameter, if present
          ...this.$route.query,
          ...params,
        },
      });
    },
  },
  methods: {
    changeSort(index) {
      if (this.sortOption === index) {
        this.sortDir *= -1;
      } else {
        this.sortOption = index;
        this.sortDir = 1;
      }

      this.page = 1;
    },
  },
};
</script>
