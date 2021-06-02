<template>
  <div v-page-title="pageTitle">
    <v-toolbar color="grey darken-2 white--text">
      <v-toolbar-title class="d-none d-md-block">
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

<script lang="ts">
import {
  defineComponent, ref, computed, watch, Ref, watchEffect,
} from '@vue/composition-api';
import DandisetList from '@/components/DandisetList.vue';
import DandisetSearchField from '@/components/DandisetSearchField.vue';
import toggles from '@/featureToggle';
import { girderRest, publishRest } from '@/rest';
import { Dandiset, Paginated } from '@/types';

const DANDISETS_PER_PAGE = 8;

const sortingOptions = [
  {
    name: 'Created',
    field: 'created',
    djangoField: 'created',
  },
  {
    name: 'Name',
    field: 'meta.dandiset.name',
    djangoField: 'name',
  },
];

export default defineComponent({
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
  setup(props, ctx) {
    // Will be replaced by `useRoute` if vue-router is upgraded to vue-router@next
    // https://next.router.vuejs.org/api/#useroute
    const route = ctx.root.$route;

    const sortOption = ref(Number(route.query.sortOption) || 0);
    const sortDir = ref(Number(route.query.sortDir || 1));
    const page = ref(Number(route.query.page) || 1);

    const pageTitle = computed(() => ((props.search) ? route.query.search as string : props.title));
    const sortField = computed(() => {
      if (toggles.DJANGO_API) {
        return sortingOptions[sortOption.value].djangoField;
      }
      return sortingOptions[sortOption.value].field;
    });

    // Django dandiset listing

    const djangoDandisetRequest: Ref<Paginated<Dandiset> | null> = ref(null);
    watchEffect(async () => {
      if (!toggles.DJANGO_API) {
        djangoDandisetRequest.value = null;
      } else {
        const ordering = ((sortDir.value === -1) ? '-' : '') + sortField.value;
        const response = await publishRest.dandisets({
          page: page.value,
          page_size: DANDISETS_PER_PAGE,
          ordering,
          user: props.user ? 'me' : null,
          search: props.search ? route.query.search : null,
        });
        djangoDandisetRequest.value = response.data;
      }
    });

    // Girder dandiset listing

    const listingUrl = computed(() => {
      if (props.user) {
        return 'dandi/user';
      }
      if (props.search) {
        return 'dandi/search';
      }
      return 'dandi';
    });
    const girderDandisetRequest: Ref<null | any> = ref(null);
    watchEffect(async () => {
      if (toggles.DJANGO_API) {
        girderDandisetRequest.value = null;
      } else {
        const {
          data, headers, status, statusText,
        } = await girderRest.get(listingUrl.value, {
          params: {
            limit: DANDISETS_PER_PAGE,
            offset: (page.value - 1) * DANDISETS_PER_PAGE,
            sort: sortField.value,
            sortdir: sortDir.value,
            search: route.query.search,
          },
        });

        girderDandisetRequest.value = {
          data, headers, status, statusText,
        };
      }
    });

    // Unified Django + Girder

    const dandisets = computed(() => {
      if (toggles.DJANGO_API) {
        return djangoDandisetRequest.value?.results.map(
          (dandiset) => dandiset.most_recent_published_version || dandiset.draft_version,
        );
      }
      return girderDandisetRequest.value?.data || [];
    });

    const pages = computed(() => {
      let totalDandisets: number;
      if (toggles.DJANGO_API) {
        totalDandisets = djangoDandisetRequest.value?.count || 0;
      } else {
        totalDandisets = girderDandisetRequest.value?.headers['girder-total-count'] || 0;
      }
      return Math.ceil(totalDandisets / DANDISETS_PER_PAGE) || 1;
    });

    const queryParams = computed(() => ({
      page: String(page.value),
      sortOption: String(sortOption.value),
      sortDir: String(sortDir.value),
    }));
    watch(queryParams, (params) => {
      ctx.root.$router.replace({
        ...route,
        // replace() takes a RawLocation, which has a name: string
        // Route has a name: string | null, so we need to tweak this
        name: route.name || undefined,
        query: {
          // do not override the search parameter, if present
          ...route.query,
          ...params,
        },
      });
    });

    function changeSort(index: number) {
      if (sortOption.value === index) {
        sortDir.value *= -1;
      } else {
        sortOption.value = index;
        sortDir.value = 1;
      }

      page.value = 1;
    }

    return {
      sortingOptions,
      sortOption,
      sortDir,
      page,
      pages,
      pageTitle,
      dandisets,
      changeSort,
    };
  },
});
</script>
