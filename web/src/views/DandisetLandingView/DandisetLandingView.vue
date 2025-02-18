<template>
  <div>
    <Meditor v-if="currentDandiset" />
    <v-toolbar class="grey darken-2 white--text">
      <DandisetSearchField />
      <v-pagination
        v-model="page"
        :length="pages"
        :total-visible="0"
      />
    </v-toolbar>
    <v-container v-if="embargoedOrUnauthenticated" class="d-flex justify-center align-center" style="height: 50vh;">
      <div class="d-block blue-grey lighten-5 pa-4 rounded-lg">
        <span class="text-h5">
          <v-icon class="mb-1">
            mdi-alert-circle
          </v-icon>
          This Dandiset is Embargoed
        </span>
        <br><br>
        <span class="text-body-2">
          If you are an owner of this Dandiset, please log in to enable access.
        </span>
        <br>
        <span class="text-body-2">
          If you are a member of this project, contact the Dandiset owners to enable access.
        </span>
        <br><br>
        <span class="text-body-2">
          For further assistance, please contact <a href="mailto:emberarchive@jhuapl.edu">emberarchive@jhuapl.edu</a>.
        </span>
      </div>
    </v-container>
    <v-container
      v-else-if="dandisetDoesNotExist"
      class="d-flex justify-center align-center"
      style="height: 50vh;"
    >
      <div class="d-block">
        <span class="text-h5">
          <v-icon>mdi-alert</v-icon>
          Error: Dandiset does not exist
        </span>
        <br><br>
        <span class="text-body-2">
          Proceed to the <a href="/dandiset">Public Dandisets page</a>
          or use the search bar to find a valid Dandiset.
        </span>
      </div>
    </v-container>
    <v-container
      v-else
      fluid
      class="grey lighten-4 pa-0"
    >
      <v-progress-linear
        v-if="!currentDandiset || loading"
        indeterminate
      />
      <v-row no-gutters>
        <v-col :cols="$vuetify.breakpoint.smAndDown ? 12 : 10">
          <v-sheet
            v-if="!currentDandiset || loading"
            class="py-8 px-7"
          >
            <v-skeleton-loader
              type="article, list-item, image@2"
            />
          </v-sheet>
          <DandisetMain
            v-else
            :schema="schema"
            :meta="meta"
          />
        </v-col>
        <v-col
          v-if="!$vuetify.breakpoint.smAndDown"
          cols="2"
        >
          <v-sheet
            v-if="!currentDandiset || loading"
            class="py-3"
          >
            <v-skeleton-loader type="card@3" />
          </v-sheet>
          <DandisetSidebar
            v-else
            :user-can-modify-dandiset="userCanModifyDandiset"
          />
        </v-col>
      </v-row>
      <v-row v-if="$vuetify.breakpoint.smAndDown">
        <v-col cols="12">
          <v-sheet
            v-if="!currentDandiset || loading"
            class="py-3"
          >
            <v-skeleton-loader type="card-heading, list-item@5" />
          </v-sheet>
          <DandisetSidebar
            v-else
            :user-can-modify-dandiset="userCanModifyDandiset"
          />
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup lang="ts">
import {
  computed, watch, onMounted, ref,
} from 'vue';
import type { Ref } from 'vue';
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router/composables';
import type { NavigationGuardNext, RawLocation, Route } from 'vue-router';

import DandisetSearchField from '@/components/DandisetSearchField.vue';
import Meditor from '@/components/Meditor/Meditor.vue';
import { useDandisetStore } from '@/stores/dandiset';
import type { Version } from '@/types';
import { draftVersion, sortingOptions } from '@/utils/constants';
import { editorInterface } from '@/components/Meditor/state';
import { dandiRest } from '@/rest';
import DandisetMain from './DandisetMain.vue';
import DandisetSidebar from './DandisetSidebar.vue';

const props = defineProps({
  identifier: {
    type: String,
    required: true,
  },
  version: {
    type: String,
    required: false,
    default: null,
  },
});

// This guards against "soft" page navigations, i.e. using the back/forward buttons or clicking
// a link to navigate elsewhere in the SPA. The `beforeunload` event listener below handles
// "hard" page navigations, such as refreshing, closing tabs, or clicking external links.
onBeforeRouteLeave((to: Route, from: Route, next: NavigationGuardNext) => {
  // Prompt user if they try to leave the DLP with unsaved changes in the meditor
  if (!editorInterface.value?.transactionTracker?.isModified()
    // eslint-disable-next-line no-alert
    || window.confirm('You have unsaved changes, are you sure you want to leave?')) {
    next();
    return true;
  }
  return false;
});

const route = useRoute();
const router = useRouter();
const store = useDandisetStore();

const currentDandiset = computed(() => store.dandiset);
const loading = ref(false);

// If loading is finished and currentDandiset is still null, the dandiset doesn't exist.
const dandisetDoesNotExist = computed(() => !loading.value && !currentDandiset.value);

// This is set if the request to retrieve the dandiset fails
// due to it being embargoed, or the user being unauthenticated
const embargoedOrUnauthenticated = ref(false);

const schema = computed(() => store.schema);
const userCanModifyDandiset = computed(() => store.userCanModifyDandiset);

const meta = computed(() => (currentDandiset.value ? currentDandiset.value.metadata : {}));

function navigateToVersion(versionToNavigateTo: string) {
  if (route.params.version === versionToNavigateTo) return;

  const newRoute = {
    ...route,
    params: {
      ...route.params,
      versionToNavigateTo,
    },
  } as RawLocation;
  router.replace(newRoute);
}

// () => props.identifier is needed since we're using Vue 2
// https://stackoverflow.com/a/59127059
watch(() => props.identifier, async () => {
  const { identifier, version } = props;
  if (!identifier) {
    return;
  }

  // Set default values
  loading.value = true;

  // Check if response is 401 or 403, for embargoed dandisets
  await store.initializeDandisets({ identifier, version });
  embargoedOrUnauthenticated.value = store.meta.dandisetExistsAndEmbargoed;

  loading.value = false;
}, { immediate: true });

watch([() => props.identifier, () => props.version], async () => {
  const { identifier, version } = props;
  loading.value = true;
  if (version) {
    // On version change, fetch the new dandiset (not initial)
    await store.fetchDandiset({ identifier, version });
  } else {
    await store.fetchDandiset({ identifier });
  }
  // If the above await call didn't result in dandiset being set, navigate to a default
  if (!currentDandiset.value) {
    // Omitting version will fetch the most recent version instead
    await store.fetchDandiset({ identifier });

    if (currentDandiset.value) {
      navigateToVersion((currentDandiset.value as Version).version);
    } else {
      // if all else fails, navigate to the draft version
      navigateToVersion(draftVersion);
    }
  }
  loading.value = false;
});

const page = ref(Number(route.query.pos) || 1);
const pages = ref(1);
const nextDandiset: Ref<any[]> = ref([]);

async function fetchNextPage() {
  const sortOption = Number(route.query.sortOption) || 0;
  const sortDir = Number(route.query.sortDir || -1);
  const sortField = sortingOptions[sortOption].djangoField;
  const ordering = ((sortDir === -1) ? '-' : '') + sortField;
  const response = await dandiRest.dandisets({
    page: page.value,
    page_size: 1,
    ordering,
    search: route.query.search,
    draft: route.query.showDrafts || true,
    empty: route.query.showEmpty,
  });

  pages.value = (response.data?.count) ? response.data?.count : 1;
  nextDandiset.value = response.data?.results.map((dandiset) => ({
    ...(dandiset.most_recent_published_version || dandiset.draft_version),
    contact_person: dandiset.contact_person,
    identifier: dandiset.identifier,
  }));
}

function navigateToPage() {
  if (nextDandiset.value) {
    const { identifier } = nextDandiset.value[0];
    if (identifier !== props.identifier) { // to avoid redundant navigation
      router.push({
        name: route.name || undefined,
        params: { identifier },
        query: {
          ...route.query,
        },
      });
    }
  }
}

watch(page, async (newValue, oldValue) => {
  if (oldValue !== newValue) {
    await fetchNextPage();
    navigateToPage();
  }
});

onMounted(async () => {
  // This guards against "hard" page navigations, i.e. refreshing, closing tabs, or
  // clicking external links. The `beforeRouteLeave` function above handles "soft"
  // page navigations, such as using the back/forward buttons or clicking a link
  // to navigate elsewhere in the SPA.
  window.addEventListener('beforeunload', (e) => {
    // display a confirmation prompt if attempting to navigate away from the
    // page with unsaved changes in the meditor
    if (editorInterface.value?.transactionTracker?.isModified()) {
      e.preventDefault();
      e.returnValue = 'You have unsaved changes, are you sure you want to leave?';
    }
  });
  await fetchNextPage(); // get the current page and total count
});
</script>
