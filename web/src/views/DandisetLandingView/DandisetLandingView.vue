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
    <v-container
      v-if="currentDandiset"
      fluid
      class="grey lighten-4 pa-0"
    >
      <v-progress-linear
        v-if="!currentDandiset || loading"
        indeterminate
      />
      <v-row no-gutters>
        <v-col :cols="$vuetify.breakpoint.smAndDown ? 12 : 10">
          <DandisetMain
            :schema="schema"
            :meta="meta"
          />
        </v-col>
        <v-col
          v-if="!$vuetify.breakpoint.smAndDown"
          cols="2"
        >
          <DandisetSidebar
            :user-can-modify-dandiset="userCanModifyDandiset"
          />
        </v-col>
      </v-row>
      <v-row v-if="$vuetify.breakpoint.smAndDown">
        <v-col cols="12">
          <DandisetSidebar
            :user-can-modify-dandiset="userCanModifyDandiset"
          />
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script lang="ts">
import {
  defineComponent, computed, watch, onMounted, Ref, ref,
} from 'vue';
import { NavigationGuardNext, RawLocation, Route } from 'vue-router';

import DandisetSearchField from '@/components/DandisetSearchField.vue';
import Meditor from '@/components/Meditor/Meditor.vue';
import { useDandisetStore } from '@/stores/dandiset';
import { Version } from '@/types';
import { draftVersion, sortingOptions } from '@/utils/constants';
import { editorInterface } from '@/components/Meditor/state';
import { dandiRest } from '@/rest';
import { useRoute, useRouter } from 'vue-router/composables';
import DandisetMain from './DandisetMain.vue';
import DandisetSidebar from './DandisetSidebar.vue';

export default defineComponent({
  name: 'DandisetLandingView',
  components: {
    DandisetMain,
    DandisetSearchField,
    DandisetSidebar,
    Meditor,
  },
  // This guards against "soft" page navigations, i.e. using the back/forward buttons or clicking a
  // link to navigate elsewhere in the SPA. The `beforeunload` event listener below handles
  // "hard" page navigations, such as refreshing, closing tabs, or clicking external links.
  //
  beforeRouteLeave(to: Route, from: Route, next: NavigationGuardNext) {
    // Prompt user if they try to leave the DLP with unsaved changes in the meditor
    if (!editorInterface.value?.transactionTracker?.isModified()
    // eslint-disable-next-line no-alert
    || window.confirm('You have unsaved changes, are you sure you want to leave?')) {
      next();
      return true;
    }
    return false;
  },
  props: {
    identifier: {
      type: String,
      required: true,
    },
    version: {
      type: String,
      required: false,
      default: null,
    },
  },
  setup(props) {
    const route = useRoute();
    const router = useRouter();
    const store = useDandisetStore();

    const currentDandiset = computed(() => store.dandiset);
    const loading = computed(() => store.loading);
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
      if (identifier) {
        await store.initializeDandisets({ identifier, version });
      }
    }, { immediate: true });

    watch([() => props.identifier, () => props.version], async () => {
      const { identifier, version } = props;
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
    });

    const page = ref(Number(route.query.pos) || 1);
    const pages = ref(1);
    const nextDandiset : Ref<any[]> = ref([]);

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

    return {
      currentDandiset,
      loading,
      schema,
      userCanModifyDandiset,
      meta,
      pages,
      page,
    };
  },
});
</script>
