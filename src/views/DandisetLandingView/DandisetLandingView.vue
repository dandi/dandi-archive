<template>
  <div
    v-if="schema"
    v-page-title="meta.name"
  >
    <template v-if="edit && Object.entries(meta).length">
      <meditor
        :schema="schema"
        :model="meta"
        :readonly="!userCanModifyDandiset"
        @close="edit = false"
      />
    </template>
    <template v-else>
      <v-toolbar class="grey darken-2 white--text">
        <v-row>
          <v-col cols="10">
            <DandisetSearchField />
          </v-col>
          <v-col>
            <DandisetStats />
          </v-col>
        </v-row>
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
          <v-col>
            <DandisetMain
              :schema="schema"
              :meta="meta"
              @edit="edit = true"
            />
          </v-col>
          <v-col
            v-if="!$vuetify.breakpoint.smAndDown"
            cols="2"
          >
            <DandisetSidebar
              :user-can-modify-dandiset="userCanModifyDandiset"
              @edit="edit = true"
            />
          </v-col>
        </v-row>
        <v-row v-if="$vuetify.breakpoint.smAndDown">
          <v-col
            cols="12"
          >
            <DandisetSidebar
              :user-can-modify-dandiset="userCanModifyDandiset"
              @edit="edit = true"
            />
          </v-col>
        </v-row>
      </v-container>
    </template>
  </div>
</template>

<script lang="ts">
import {
  defineComponent, ref, computed, watchEffect, watch, Ref, ComputedRef,
} from '@vue/composition-api';
import { RawLocation } from 'vue-router';

import DandisetSearchField from '@/components/DandisetSearchField.vue';
import DandisetStats from '@/components/DandisetStats.vue';
import { user as userFunc } from '@/rest';
import { User, Version } from '@/types';
import Meditor from './Meditor.vue';
import DandisetMain from './DandisetMain.vue';
import DandisetSidebar from './DandisetSidebar.vue';

export default defineComponent({
  name: 'DandisetLandingView',
  components: {
    Meditor,
    DandisetMain,
    DandisetSearchField,
    DandisetStats,
    DandisetSidebar,
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
    const { identifier, version } = props;

    const store = ctx.root.$store;

    const currentDandiset: ComputedRef<Version> = computed(
      () => store.state.dandiset.publishDandiset,
    );
    const loading: ComputedRef<boolean> = computed(() => store.state.dandiset.loading);
    const schema: ComputedRef<any> = computed(() => store.state.dandiset.schema);
    const user: ComputedRef<User|null> = computed(userFunc);
    const meta: ComputedRef<any> = computed(() => (
      currentDandiset.value ? currentDandiset.value.metadata : {}
    ));

    const edit: Ref<boolean> = ref(false);
    const readonly: Ref<boolean> = ref(false);

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

    const userCanModifyDandiset: ComputedRef<boolean> = computed(
      () => store.getters['dandiset/userCanModifyDandiset'],
    );

    // () => identifier is needed since we're using Vue 2
    // https://stackoverflow.com/a/59127059
    watch(() => identifier, async () => {
      if (identifier) {
        await store.dispatch('dandiset/initializeDandisets', { identifier, version });
      }
    }, { immediate: true });

    watchEffect(async () => {
      // On version change, fetch the new dandiset (not initial)
      await store.dispatch('dandiset/fetchPublishDandiset', { identifier, version });
      // If the above await call didn't result in publishDandiset being set, navigate to a default
      if (!currentDandiset) {
        // Omitting version will fetch the most recent version instead
        await store.dispatch('dandiset/fetchPublishDandiset', { identifier });
        navigateToVersion((currentDandiset as Version).version);
      }
    });

    return {
      currentDandiset,
      loading,
      schema,
      user,
      userCanModifyDandiset,
      edit,
      readonly,
      meta,
    };
  },
});
</script>
