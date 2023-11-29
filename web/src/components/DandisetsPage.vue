<template>
  <div v-page-title="pageTitle">
    <v-toolbar color="grey darken-2 white--text">
      <v-menu
        v-if="!user"
        offset-y
        :close-on-content-click="false"
      >
        <template #activator="{ on, attrs }">
          <v-icon
            dark
            v-bind="attrs"
            v-on="on"
          >
            mdi-cog
          </v-icon>
        </template>
        <v-list>
          <v-list-item>
            <v-list-item-title>Show:</v-list-item-title>
          </v-list-item>
          <v-list-item>
            <v-switch
              v-model="showDrafts"
              label="Drafts"
              dense
            />
          </v-list-item>
          <v-list-item>
            <v-switch
              v-model="showEmpty"
              label="Empty Dandisets"
              dense
            />
          </v-list-item>
        </v-list>
      </v-menu>
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
      class="mx-4 mx-md-8 my-8"
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
import type { Ref, ComputedRef } from 'vue';
import {
  defineComponent, ref, computed, watch, watchEffect,
} from 'vue';

import omit from 'lodash/omit';
import { useRoute } from 'vue-router/composables';
import DandisetList from '@/components/DandisetList.vue';
import DandisetSearchField from '@/components/DandisetSearchField.vue';
import { dandiRest } from '@/rest';
import type { Dandiset, Paginated, Version } from '@/types';
import { sortingOptions, DANDISETS_PER_PAGE } from '@/utils/constants';
import router from '@/router';

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
  setup(props) {
    const route = useRoute();

    const showDrafts = ref(true);
    const showEmpty = ref(false);
    const sortOption = ref(Number(route.query.sortOption) || 0);
    const sortDir = ref(Number(route.query.sortDir || -1));
    const page = ref(Number(route.query.page) || 1);

    const pageTitle = computed(() => ((props.search) ? route.query.search as string : props.title));
    const sortField = computed(() => sortingOptions[sortOption.value].djangoField);

    // Django dandiset listing

    const djangoDandisetRequest: Ref<Paginated<Dandiset> | null> = ref(null);
    watchEffect(async () => {
      const ordering = ((sortDir.value === -1) ? '-' : '') + sortField.value;
      const response = await dandiRest.dandisets({
        page: page.value,
        page_size: DANDISETS_PER_PAGE,
        ordering,
        user: props.user ? 'me' : null,
        search: props.search ? route.query.search : null,
        draft: props.user ? true : showDrafts.value,
        empty: props.user ? true : showEmpty.value,
        embargoed: props.user,
      });
      djangoDandisetRequest.value = response.data;
    });

    const dandisets = computed(
      () => djangoDandisetRequest.value?.results.map((dandiset) => ({
        ...(dandiset.most_recent_published_version || dandiset.draft_version),
        dandiset: omit(dandiset, 'most_recent_published_version', 'draft_version'),
      })),
    ) as ComputedRef<Version[] | undefined>;

    const pages = computed(() => {
      const totalDandisets: number = djangoDandisetRequest.value?.count || 0;
      return Math.ceil(totalDandisets / DANDISETS_PER_PAGE) || 1;
    });

    watch([showDrafts, showEmpty], () => {
      page.value = 1;
    });

    const queryParams = computed(() => ({
      page: String(page.value),
      sortOption: String(sortOption.value),
      sortDir: String(sortDir.value),
      showDrafts: String(showDrafts.value),
      showEmpty: String(showEmpty.value),
    }));
    watch(queryParams, (params) => {
      router.replace({
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
      showDrafts,
      showEmpty,
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
