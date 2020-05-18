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
      <v-container fluid>
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
import filesize from 'filesize';
import { mapState } from 'vuex';

import { dandiUrl } from '@/utils';
import girderRest, { loggedIn } from '@/rest';

import SCHEMA from '@/assets/schema/dandiset.json';
import NEW_SCHEMA from '@/assets/schema/dandiset_new.json';
import NWB_SCHEMA from '@/assets/schema/dandiset_metanwb.json';

import DandisetSearchField from '@/components/DandisetSearchField.vue';
import ListingComponent from './ListingComponent.vue';
import MetaEditor from './MetaEditor.vue';
import DandisetData from './DandisetData.vue';
import DandisetDetails from './DandisetDetails.vue';

export default {
  name: 'DandisetLandingView',
  components: {
    MetaEditor,
    DandisetData,
    ListingComponent,
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
      dandiUrl,
      meta: {},
      edit: false,
      published: false,
      uploader: '',
      last_modified: null,
      details: null,
      detailsPanel: true,
      mainFields: [
        'name',
        'version',
        'contributors',
        'description',
        'identifier',
      ],
    };
  },
  computed: {
    editDisabledMessage() {
      if (!loggedIn) {
        return 'You must be logged in to edit.';
      }

      if (this.selected._accessLevel < 1) {
        return 'You do not have permission to edit this dandiset.';
      }

      return null;
    },
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
    permalink() {
      return `${this.dandiUrl}/dandiset/${this.meta.identifier}/draft`;
    },
    extraFields() {
      const { meta, mainFields } = this;
      const extra = Object.keys(meta).filter(
        (x) => !mainFields.includes(x) && x in this.schema.properties,
      );
      return extra.reduce((obj, key) => ({ ...obj, [key]: meta[key] }), {});
    },
    computedSize() {
      if (!this.selected || !this.selected.size) return null;
      return filesize(this.selected.size);
    },
    ...mapState('girder', {
      selected: (state) => state.currentDandiset,
    }),
  },
  watch: {
    async selected(val) {
      if (!val || !val.meta || !val.meta.dandiset) {
        this.meta = {};
        return;
      }

      this.meta = { ...val.meta.dandiset };
      this.last_modified = new Date(val.updated).toString();

      let res = await girderRest.get(`/user/${val.creatorId}`);
      if (res.status === 200) {
        const { data: { firstName, lastName } } = res;
        this.uploader = `${firstName} ${lastName}`;
      }

      res = await girderRest.get(`/folder/${val._id}/details`);
      if (res.status === 200) {
        this.details = res.data;
      }
    },
    id: {
      immediate: true,
      async handler(value) {
        if (!this.selected || !this.meta.length) {
          const { data } = await girderRest.get(`folder/${value}`);
          this.$store.commit('girder/setCurrentDandiset', data);
        }
      },
    },
  },
};
</script>
