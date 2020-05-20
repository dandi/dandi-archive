<template>
  <div>
    <v-row class="mx-2 my-2">
      <h1 class="font-weight-regular">
        {{ meta.name }}
      </h1>
    </v-row>
    <v-card>
      <v-row
        class="mx-2"
        align-content="center"
      >
        <v-col>
          <a :href="permalink">
            {{ permalink }}
          </a>
        </v-col>
        <v-tooltip
          left
          :disabled="editDisabledMessage === null"
        >
          <template v-slot:activator="{ on }">
            <div v-on="on">
              <v-btn
                class="mt-2"
                text
                :disabled="editDisabledMessage !== null"
                @click="$emit('edit')"
              >
                <v-icon class="mr-3 ml-0">
                  mdi-pencil
                </v-icon>
                Edit metadata
              </v-btn>
            </div>
          </template>
          {{ editDisabledMessage }}
        </v-tooltip>
      </v-row>

      <v-divider />

      <v-row :class="titleClasses">
        <v-card-title class="font-weight-regular">
          Description
        </v-card-title>
      </v-row>
      <v-row class="mx-1 px-4 font-weight-light">
        {{ meta.description }}
      </v-row>

      <template v-for="(field, key) in extraFields">
        <v-divider
          :key="`${key}-divider`"
          class="mt-4"
        />
        <v-row
          :key="`${key}-title`"
          :class="titleClasses"
        >
          <v-card-title class="font-weight-regular">
            {{ schema.properties[key].title }}
          </v-card-title>
        </v-row>
        <v-row
          :key="key"
          class="mx-4"
        >
          <v-col class="py-0">
            <ListingComponent
              :schema="schema.properties[key]"
              :data="field"
              root
            />
          </v-col>
        </v-row>
      </template>
    </v-card>
  </div>
</template>

<script>
import { mapState } from 'vuex';

import { dandiUrl } from '@/utils';
import { loggedIn } from '@/rest';

import ListingComponent from './ListingComponent.vue';

export default {
  name: 'DandisetData',
  components: {
    ListingComponent,
  },
  props: {
    schema: {
      type: Object,
      required: true,
    },
    meta: {
      type: Object,
      required: true,
    },
  },
  data() {
    return {
      titleClasses: 'mx-1',
      mainFields: [
        'name',
        'description',
      ],
    };
  },
  computed: {
    loggedIn,
    editDisabledMessage() {
      if (!this.loggedIn) {
        return 'You must be logged in to edit.';
      }

      if (!this.currentDandiset) {
        return null;
      }

      if (this.currentDandiset._accessLevel < 1) {
        return 'You do not have permission to edit this dandiset.';
      }

      return null;
    },
    permalink() {
      return `${dandiUrl}/dandiset/${this.meta.identifier}/draft`;
    },
    extraFields() {
      const { meta, mainFields } = this;
      const extra = Object.keys(meta).filter(
        (x) => !mainFields.includes(x) && x in this.schema.properties,
      );
      return extra.reduce((obj, key) => ({ ...obj, [key]: meta[key] }), {});
    },
    ...mapState('girder', {
      currentDandiset: (state) => state.currentDandiset,
    }),
  },
};
</script>
