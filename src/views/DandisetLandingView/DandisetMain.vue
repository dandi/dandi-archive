<template>
  <div>
    <v-card
      class="px-3"
      outlined
    >
      <v-row class="mx-2 my-2 mb-0">
        <v-col>
          <h1 class="font-weight-light">
            {{ meta.name }}
          </h1>
        </v-col>
      </v-row>
      <v-row class="mx-1">
        <v-col cols="3">
          <v-chip
            outlined
          >
            <v-row>
              <v-col :cols="currentDandiset.version === 'draft' ? '6' : '5'">
                <span class="pr-3">ID: {{ currentDandiset.dandiset.identifier }}</span>
              </v-col>
              <v-col
                :class="`${currentDandiset.version === 'draft' ? 'orange' : 'blue'} lighten-4`"
              >
                <span
                  :class="`
                    ${currentDandiset.version === 'draft' ? 'orange' : 'blue'}--text text--darken-4
                  `"
                >
                  {{ currentDandiset.version.toUpperCase() }}
                </span>
              </v-col>
            </v-row>
          </v-chip>
        </v-col>
        <v-col cols="3">
          <span>
            <v-icon class="grey--text text--lighten-1">mdi-account</v-icon>
            Contact <strong>{{ currentDandiset.contact_person }}</strong>
          </span>
        </v-col>
        <v-col cols="3">
          <span>
            <v-icon class="grey--text text--lighten-1">mdi-calendar-range</v-icon>
            Created <strong>{{ formatDate(currentDandiset.created) }}</strong>
          </span>
        </v-col>
        <v-col cols="3">
          <span>
            <v-icon class="grey--text text--lighten-1">mdi-history</v-icon>
            Last update <strong>{{ formatDate(currentDandiset.modified) }}</strong>
          </span>
        </v-col>
      </v-row>

      <v-divider />

      <v-row class="mx-1 my-4 px-4 font-weight-light">
        {{ meta.description }}
      </v-row>

      <v-row class="justify-center">
        <v-col
          cols="11"
          class="pb-0"
        >
          <v-card
            v-if="(meta.keywords && meta.keywords.length) || (meta.license && meta.license.length)"
            outlined
            class="mb-4"
          >
            <v-card-text
              v-if="meta.keywords.length"
              style="border-bottom: thin solid rgba(0, 0, 0, 0.12);"
            >
              Keywords:
              <v-chip
                v-for="(keyword, i) in meta.keywords"
                :key="i"
                small
                style="margin: 5px;"
              >
                {{ keyword }}
              </v-chip>
            </v-card-text>

            <v-card-text v-if="meta.license.length">
              Licenses:
              <v-chip
                v-for="(license, i) in meta.license"
                :key="i"
                small
                style="margin: 5px;"
              >
                {{ license }}
              </v-chip>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- // TODO: remove when redesign is implemented -->
      <template v-for="key in Object.keys(extraFields).sort()">
        <template v-if="renderData(extraFields[key], schema.properties[key])">
          <v-divider :key="`${key}-divider`" />
          <v-row
            :key="`${key}-title`"
            class="mx-1"
          >
            <v-card-title class="font-weight-regular">
              {{ schemaPropertiesCopy[key].title || key }}
            </v-card-title>
          </v-row>
          <v-row
            :key="key"
            class="mx-2 mb-4"
          >
            <v-col class="py-0">
              <ListingComponent
                :field="key"
                :schema="schema.properties[key]"
                :data="extraFields[key]"
              />
            </v-col>
          </v-row>
        </template>
      </template>
    </v-card>
  </div>
</template>

<script lang="ts">
import {
  defineComponent, ref, computed, ComputedRef, Ref,
} from '@vue/composition-api';

import moment from 'moment';

import _ from 'lodash';

import { Version } from '@/types';

import ListingComponent from './ListingComponent.vue';

// TODO: remove when redesign is implemented
function renderData(data: any, schema: any) {
  if (data === null || _.isEmpty(data)) {
    return false;
  }
  if (schema.type === 'array' && Array.isArray(data) && data.length === 0) {
    return false;
  }
  return true;
}

export default defineComponent({
  name: 'DandisetMain',
  components: { ListingComponent },
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
  setup(props, ctx) {
    const { meta, schema } = props;
    const store = ctx.root.$store;

    const currentDandiset: ComputedRef<Version> = computed(
      () => store.state.dandiset.publishDandiset,
    );

    const currentTab: Ref<string> = ref('');

    function formatDate(date: string): string {
      return moment(date).format('LL');
    }

    // TODO: remove when redesign is implemented
    const extraFields = computed(() => {
      const mainFields = ['name', 'description', 'identifier'];
      let extra = Object.keys(meta).filter(
        (x) => !mainFields.includes(x) && x in schema.properties,
      );
      const remove_list = ['citation', 'repository', 'url', 'schemaVersion', 'version', 'id', 'keywords', 'schemaKey'];
      extra = extra.filter((n) => !remove_list.includes(n));
      const extra_obj: any = extra.reduce((obj, key) => ({ ...obj, [key]: meta[key] }), {});
      extra_obj.contributor = _.filter(meta.contributor, (author) => author.schemaKey !== 'Person');
      delete extra_obj.assetsSummary.schemaKey;
      delete extra_obj.assetsSummary.numberOfBytes;
      delete extra_obj.assetsSummary.numberOfFiles;
      _.forEach(extra_obj, (val) => {
        if (Array.isArray(val) && val.length !== 0) {
          val.forEach((each_val) => {
            if (Object.prototype.hasOwnProperty.call(each_val, 'schemaKey')) {
              /* eslint no-param-reassign:["error",
              {"ignorePropertyModificationsFor":["each_val"] }] */
              delete each_val.schemaKey;
            }
          });
        }
      });
      return extra_obj;
    });

    // TODO: remove when redesign is implemented
    const schemaPropertiesCopy = computed(() => {
      const schema_copy = JSON.parse(JSON.stringify(schema.properties));
      schema_copy.contributor.title = 'Funding Information';
      return schema_copy;
    });

    return {
      currentDandiset,
      formatDate,
      currentTab,

      renderData,
      extraFields,
      schemaPropertiesCopy,
    };
  },
});
</script>
