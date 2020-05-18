<template>
  <div v-page-title="meta.name">
    <meta-editor
      v-if="edit && Object.entries(meta).length"
      :schema="schema"
      :model="meta"
      :create="create"
      @close="edit = false"
    />
    <template v-else>
      <v-toolbar class="grey darken-2 white--text">
        <v-btn
          icon
          @click="$router.go(-1)"
        >
          <v-icon color="white">
            mdi-arrow-left
          </v-icon>
        </v-btn>
        <v-toolbar-title>
          Dandiset Dashboard
        </v-toolbar-title>
        <v-spacer />
        <DandisetSearchField />
        <v-btn
          icon
          @click="detailsPanel = !detailsPanel"
        >
          <v-icon color="white">
            <template v-if="detailsPanel">
              mdi-chevron-right
            </template>
            <template v-else>
              mdi-chevron-left
            </template>
          </v-icon>
        </v-btn>
      </v-toolbar>
      <v-container
        fluid
        class="grey lighten-4"
      >
        <v-row>
          <v-col>
            <DandisetData
              :schema="schema"
              :meta="meta"
              @edit="edit = true"
            />
          </v-col>
          <v-col
            v-if="detailsPanel"
            cols="auto"
          >
            <DandisetDetails />
          </v-col>
        </v-row>
      </v-container>
    </template>
  </div>
</template>

<script>
import { mapState } from 'vuex';

import girderRest from '@/rest';

import SCHEMA from '@/assets/schema/dandiset.json';
import NEW_SCHEMA from '@/assets/schema/dandiset_new.json';
import NWB_SCHEMA from '@/assets/schema/dandiset_metanwb.json';

import DandisetSearchField from '@/components/DandisetSearchField.vue';
import MetaEditor from './MetaEditor.vue';
import DandisetData from './DandisetData.vue';
import DandisetDetails from './DandisetDetails.vue';

export default {
  name: 'DandisetLandingView',
  components: {
    MetaEditor,
    DandisetData,
    DandisetSearchField,
    DandisetDetails,
  },
  props: {
    id: {
      type: String,
      required: true,
    },
    create: {
      type: Boolean,
      required: false,
      default: () => false,
    },
  },
  data() {
    return {
      edit: false,
      detailsPanel: true,
    };
  },
  computed: {
    schema() {
      if (this.create) {
        return NEW_SCHEMA;
      }

      if (this.edit) {
        return SCHEMA;
      }

      const properties = { ...SCHEMA.properties, ...NWB_SCHEMA.properties };
      const required = [...SCHEMA.required, ...NWB_SCHEMA.required];

      return { properties, required };
    },
    meta() {
      if (
        !this.currentDandiset
        || !this.currentDandiset.meta
        || !this.currentDandiset.meta.dandiset
      ) {
        return {};
      }

      return { ...this.currentDandiset.meta.dandiset };
    },
    ...mapState('girder', {
      currentDandiset: (state) => state.currentDandiset,
    }),
  },
  watch: {
    id: {
      immediate: true,
      async handler(value) {
        // If we ever change the URL to contain the dandiset ID instead of the
        // girder folder ID, this should be moved into the store

        if (!this.currentDandiset || !this.meta.length) {
          const { data } = await girderRest.get(`folder/${value}`);
          this.$store.commit('girder/setCurrentDandiset', data);
        }
      },
    },
  },
};
</script>
