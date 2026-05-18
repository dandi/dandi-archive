<template>
  <div>
    <Meditor
      v-if="currentDandiset"
      :key="`${currentDandiset.dandiset.identifier}/${currentDandiset.version}`"
    />
    <v-toolbar class="px-4 bg-grey-darken-2 text-white">
      <DandisetSearchField />
      <v-pagination
        v-if="hasListingContext"
        v-model="page"
        :length="pages"
        :total-visible="0"
      />
    </v-toolbar>
    <v-container
      v-if="embargoedOrUnauthenticated"
      class="d-flex justify-center align-center"
      style="height: 50vh;"
    >
      <div class="d-block bg-blue-grey-lighten-5 pa-4 rounded-lg">
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
          For further assistance, please contact <a href="mailto:help@dandiarchive.org">help@dandiarchive.org</a>.
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
      class="bg-grey-lighten-4 pa-0"
    >
      <v-progress-linear
        v-if="!currentDandiset || loading"
        indeterminate
      />
      <v-row no-gutters>
        <v-col :cols="isSmDisplay ? 12 : 10">
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
          v-if="!isSmDisplay"
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
      <v-row v-if="isSmDisplay">
        <v-col cols="12">
          <v-sheet
            v-if="!currentDandiset || loading"
            class="py-3"
          >
            <v-skeleton-loader type="card, list-item@5" />
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
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router';
import type { RouteLocationRaw } from 'vue-router';
import { useDisplay } from 'vuetify';

import DandisetSearchField from '@/components/DandisetSearchField.vue';
import Meditor from '@/components/Meditor/Meditor.vue';
import { useDandisetStore } from '@/stores/dandiset';
import type { Version } from '@/types';
import { draftVersion, sortingOptions } from '@/utils/constants';
import { editorInterface, open as meditorOpen } from '@/components/Meditor/state';
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
onBeforeRouteLeave((to, from, next) => {
  // Prompt user if they try to leave the DLP with unsaved changes in the meditor
  if (!editorInterface.value?.transactionTracker?.isModified()
    || window.confirm('You have unsaved changes, are you sure you want to leave?')) {
    next();
    return true;
  }
  return false;
});

const route = useRoute();
const router = useRouter();
const store = useDandisetStore();
const display = useDisplay();

const isSmDisplay = computed(() => display.smAndDown.value);

// Sync meditor open/close state with ?overlay=meditor URL query param.
if (route.query.overlay === 'meditor') {
  meditorOpen.value = true;
}
watch(meditorOpen, (isOpen) => {
  const hasParam = route.query.overlay === 'meditor';
  if (isOpen && !hasParam) {
    router.replace({ ...route, query: { ...route.query, overlay: 'meditor' } });
  } else if (!isOpen && hasParam) {
    const query = { ...route.query };
    delete query.overlay;
    router.replace({ ...route, query });
  }
});

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
  } as RouteLocationRaw;
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

// Listing pagination — uses history.state for search context (invisible in URL)
// and ?pos= for position (visible, survives reload).  Cached identifiers from
// the listing page allow instant prev/next without additional API calls.

interface ListingCtx {
  sortOption: number; sortDir: number; search: string | null;
  showDrafts: boolean; showEmpty: boolean;
}

// Read listing context reactively from history.state on each route change.
const listingState = computed(() => {
  // Access route.fullPath to create a reactive dependency on route changes.
  // eslint-disable-next-line @typescript-eslint/no-unused-expressions
  route.fullPath;
  return {
    ctx: window.history.state?.listingContext as ListingCtx | undefined,
    cachedIds: (window.history.state?.cachedIds ?? []) as string[],
    cachedOffset: (window.history.state?.cachedOffset ?? 0) as number,
  };
});

const hasListingContext = computed(
  () => Number(route.query.pos) > 0 && !!listingState.value.ctx,
);
const page = ref(Number(route.query.pos) || 0);
const pages = ref(1);

// Keep `page` in sync when the route's ?pos= changes (e.g. after navigateToDandiset).
watch(() => Number(route.query.pos) || 0, (newPos) => {
  if (newPos !== page.value) {
    page.value = newPos;
  }
});

// Try to resolve an identifier from the cache (pos is 1-based).
function cachedIdentifierAt(pos: number): string | null {
  const { cachedIds, cachedOffset } = listingState.value;
  const idx = pos - 1 - cachedOffset;
  if (idx >= 0 && idx < cachedIds.length) {
    return cachedIds[idx];
  }
  return null;
}

// Fallback: fetch one result at the given position from the listing API.
async function fetchIdentifierAt(pos: number): Promise<string | null> {
  const ctx = listingState.value.ctx;
  if (!ctx) return null;
  const sortField = sortingOptions[ctx.sortOption].djangoField;
  const ordering = ((ctx.sortDir === -1) ? '-' : '') + sortField;
  const response = await dandiRest.dandisets({
    page: pos,
    page_size: 1,
    ordering,
    search: ctx.search,
    draft: ctx.showDrafts,
    empty: ctx.showEmpty,
  });
  pages.value = response.data?.count ?? 1;
  const results = response.data?.results;
  return results?.[0]?.identifier ?? null;
}

function navigateToDandiset(identifier: string, pos: number) {
  if (identifier === props.identifier) return;
  const { ctx, cachedIds, cachedOffset } = listingState.value;
  const search = (route.query.search as string) || undefined;
  router.push({
    name: route.name || undefined,
    params: { identifier },
    query: { pos: String(pos), ...(search ? { search } : {}) },
    state: {
      listingContext: ctx ? { ...ctx } : undefined,
      cachedIds,
      cachedOffset,
    },
  });
}

// When the user clicks prev/next, resolve the identifier and navigate.
watch(page, async (newPos, oldPos) => {
  if (oldPos === newPos || newPos < 1) return;

  const identifier = cachedIdentifierAt(newPos) ?? await fetchIdentifierAt(newPos);
  if (identifier) {
    navigateToDandiset(identifier, newPos);
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
  if (hasListingContext.value) {
    // Fetch total count so the pagination component knows the length.
    // If we have cache, we might still need the count from the API.
    await fetchIdentifierAt(page.value);
  }
});
</script>
