<template>
  <div v-page-title="pageTitle">
    <v-toolbar
      color="grey-darken-2"
      class="px-4"
    >
      <v-menu
        v-if="!user"
        :close-on-content-click="false"
      >
        <template #activator="{ props: menuProps }">
          <v-icon
            v-bind="menuProps"
            class="mr-6"
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
              density="compact"
              class="mx-2"
              color="primary"
            />
          </v-list-item>
          <v-list-item>
            <v-switch
              v-model="showEmpty"
              label="Empty Dandisets"
              density="compact"
              class="mx-2"
              color="primary"
            />
          </v-list-item>
        </v-list>
      </v-menu>
      <DandisetSearchField class="flex-grow-1 mr-2" />
      <v-btn
        variant="flat"
      >
        <span class="pr-2">
          <span
            v-if="sortDir === 1"
          >
            <v-icon>mdi-sort-reverse-variant</v-icon>
            <v-icon>mdi-arrow-up-thin</v-icon>
          </span>
          <span v-else>
            <v-icon>mdi-sort-variant</v-icon>
            <v-icon>mdi-arrow-down-thin</v-icon>
          </span>
        </span>
        <span
          class="d-none d-sm-inline"
        >
          {{ sortingOptions[sortOption].name }}
        </span>
        <v-tooltip
          location="top"
          activator="parent"
        >
          <span>Sorting Options</span>
        </v-tooltip>
        <v-menu activator="parent">
          <v-list>
            <v-item-group v-model="sortOption">
              <v-list-subheader
                class="text-high-emphasis font-weight-bold"
              >
                Sort by
              </v-list-subheader>
              <v-item
                v-for="(option, i) in sortingOptions"
                :key="option.name"
                v-slot="{ isSelected, toggle }"
                :value="i"
              >
                <v-list-item
                  class="pl-8"
                  :active="isSelected"
                  @click="toggle"
                >
                  <template #append>
                    <v-icon v-if="isSelected">
                      mdi-check
                    </v-icon>
                  </template>
                  <v-list-item-title>{{ option.name }}</v-list-item-title>
                </v-list-item>
              </v-item>
            </v-item-group>
            <v-divider />
            <v-item-group v-model="sortDir">
              <v-list-subheader
                class="text-high-emphasis font-weight-bold"
              >
                Order
              </v-list-subheader>
              <v-item
                v-slot="{ isSelected, toggle }"
                :value="1"
              >
                <v-list-item
                  class="pl-8"
                  :active="isSelected"
                  @click="toggle"
                >
                  <template #append>
                    <v-icon v-if="sortDir === 1">
                      mdi-check
                    </v-icon>
                  </template>
                  <v-list-item-title>Ascending</v-list-item-title>
                </v-list-item>
              </v-item>
              <v-item
                v-slot="{ isSelected, toggle }"
                :value="-1"
              >
                <v-list-item
                  class="pl-8"
                  :active="isSelected"
                  @click="toggle"
                >
                  <template #append>
                    <v-icon v-if="sortDir === -1">
                      mdi-check
                    </v-icon>
                  </template>
                  <v-list-item-title>Descending</v-list-item-title>
                </v-list-item>
              </v-item>
            </v-item-group>
          </v-list>
        </v-menu>
      </v-btn>
    </v-toolbar>
    <div
      v-if="props.search && djangoDandisetRequest"
      class="mx-4 mx-md-8 mt-4 text-h6"
    >
      {{ djangoDandisetRequest.count }} {{ djangoDandisetRequest.count === 1 ? 'result' : 'results' }} found
    </div>
    <DandisetList
      v-if="dandisets && dandisets.length"
      :dandisets="dandisets"
    />
    <v-container v-else>
      <v-row
        class="text-center ma-12 text-grey"
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

<script setup lang="ts">
import type { Ref, ComputedRef } from 'vue';
import {
  ref, computed, watch, watchEffect,
} from 'vue';

import omit from 'lodash/omit';
import { useRoute } from 'vue-router';
import DandisetList from '@/components/DandisetList.vue';
import DandisetSearchField from '@/components/DandisetSearchField.vue';
import { dandiRest } from '@/rest';
import type { Dandiset, Paginated, Version } from '@/types';
import { sortingOptions, DANDISETS_PER_PAGE } from '@/utils/constants';
import router from '@/router';

const props = defineProps({
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
  starred: {
    type: Boolean,
    required: false,
    default: false,
  },
})

const route = useRoute();

const showDrafts = ref(true);
const showEmpty = ref(props.search);
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
    starred: props.starred ? true : null,
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
    query: {
      // do not override the search parameter, if present
      ...route.query,
      ...params,
    },
  });
});
</script>

<style scoped>
.btn-group--sort-options {
  min-width: 84px;
}

.btn--sort-option {
  min-width: 56px;
}

.btn--sort-order {
  min-width: 28px;
}
</style>
