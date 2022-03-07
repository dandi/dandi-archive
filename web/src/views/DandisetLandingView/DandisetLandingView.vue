<template>
  <div>
    <v-toolbar class="grey darken-2 white--text">
      <DandisetSearchField />
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
  defineComponent, computed, watchEffect, watch, onMounted,
} from '@vue/composition-api';
import { NavigationGuardNext, RawLocation, Route } from 'vue-router';

import DandisetSearchField from '@/components/DandisetSearchField.vue';
import store from '@/store';
import { Version } from '@/types';
import { draftVersion } from '@/utils/constants';
import { editorInterface } from '@/components/Meditor/state';
import DandisetMain from './DandisetMain.vue';
import DandisetSidebar from './DandisetSidebar.vue';

export default defineComponent({
  name: 'DandisetLandingView',
  components: {
    DandisetMain,
    DandisetSearchField,
    DandisetSidebar,
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
  setup(props, ctx) {
    const currentDandiset = computed(() => store.state.dandiset.dandiset);
    const loading = computed(() => store.state.dandiset.loading);
    const schema = computed(() => store.state.dandiset.schema);
    const userCanModifyDandiset = computed(() => store.getters.dandiset.userCanModifyDandiset);

    const meta = computed(() => (currentDandiset.value ? currentDandiset.value.metadata : {}));

    function navigateToVersion(versionToNavigateTo: string) {
      if (ctx.root.$route.params.version === versionToNavigateTo) return;

      const route = {
        ...ctx.root.$route,
        params: {
          ...ctx.root.$route.params,
          versionToNavigateTo,
        },
      } as RawLocation;
      ctx.root.$router.replace(route);
    }

    // () => props.identifier is needed since we're using Vue 2
    // https://stackoverflow.com/a/59127059
    watch(() => props.identifier, async () => {
      const { identifier, version } = props;
      if (identifier) {
        await store.dispatch.dandiset.initializeDandisets({ identifier, version });
      }
    }, { immediate: true });

    watchEffect(async () => {
      const { identifier, version } = props;
      if (version) {
      // On version change, fetch the new dandiset (not initial)
        await store.dispatch.dandiset.fetchDandiset({ identifier, version });
      } else {
        await store.dispatch.dandiset.fetchDandiset({ identifier });
      }
      // If the above await call didn't result in dandiset being set, navigate to a default
      if (!currentDandiset.value) {
        // Omitting version will fetch the most recent version instead
        await store.dispatch.dandiset.fetchDandiset({ identifier });

        if (currentDandiset.value) {
          navigateToVersion((currentDandiset.value as Version).version);
        } else {
          // if all else fails, navigate to the draft version
          navigateToVersion(draftVersion);
        }
      }
    });

    onMounted(() => {
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
    });

    return {
      currentDandiset,
      loading,
      schema,
      userCanModifyDandiset,
      meta,
    };
  },
});
</script>
