<template>
  <div>
    <v-card
      class="px-3"
      outlined
    >
      <v-row class="mx-2 my-2 mb-0">
        <v-col>
          <h1 :class="`font-weight-light ${$vuetify.breakpoint.xs ? 'text-h6' : ''}`">
            {{ meta.name }}
            <ShareableLinkDialog>
              <template
                #activator="{ on }"
                class="justify-left"
              >
                <v-icon
                  color="primary"
                  left
                  v-on="on"
                >
                  mdi-link
                </v-icon>
              </template>
            </ShareableLinkDialog>
            <ShareDialog v-if="$vuetify.breakpoint.xs" />
          </h1>
        </v-col>
      </v-row>
      <v-row class="mx-1">
        <v-col :cols="$vuetify.breakpoint.xs ? 12 : 3">
          <v-chip
            class="text-wrap py-1"
            style="text-align: center;"
            outlined
          >
            <span>
              ID: <span class="font-weight-bold">{{ currentDandiset.dandiset.identifier }}</span>
            </span>
            <v-divider
              vertical
              class="mx-2"
            />
            <span
              :class="`
                font-weight-bold
                ${currentDandiset.version === 'draft' ? 'orange' : 'blue'}--text text--darken-4
              `"
            >
              {{ currentDandiset.version.toUpperCase() }}
            </span>
          </v-chip>
        </v-col>
        <v-col :cols="$vuetify.breakpoint.xs ? 12 : 3">
          <span>
            <v-icon class="grey--text text--lighten-1">mdi-account</v-icon>
            Contact <strong>{{ currentDandiset.contact_person }}</strong>
          </span>
        </v-col>
        <v-col :cols="$vuetify.breakpoint.xs ? 12 : 3">
          <span>
            <v-icon class="grey--text text--lighten-1">mdi-file</v-icon>
            File Count <strong>{{ stats.asset_count }}</strong>
          </span>
        </v-col>
        <v-col :cols="$vuetify.breakpoint.xs ? 12 : 3">
          <span>
            <v-icon class="grey--text text--lighten-1">mdi-server</v-icon>
            File Size <strong>{{ filesize(stats.size) }}</strong>
          </span>
        </v-col>
      </v-row>
      <v-row
        class="mx-1"
      >
        <v-col :cols="$vuetify.breakpoint.xs ? 12 : 6">
          <span>
            <v-icon class="grey--text text--lighten-1">mdi-calendar-range</v-icon>
            Created <strong>{{ formatDate(currentDandiset.created) }}</strong>
          </span>
        </v-col>
        <v-col :cols="$vuetify.breakpoint.xs ? 12 : 6">
          <span>
            <v-icon class="grey--text text--lighten-1">mdi-history</v-icon>
            Last update <strong>{{ formatDate(currentDandiset.modified) }}</strong>
          </span>
        </v-col>
      </v-row>

      <v-divider />
      <!-- TODO: delete this component after redesigned contributors list is implemented -->
      <DandisetContributors />

      <v-row class="mx-1 my-4 px-4 font-weight-light">
        <!-- Truncate text if necessary -->
        <span v-if="meta.description && (meta.description.length > MAX_DESCRIPTION_LENGTH)">
          {{ description }}
          <a
            v-if="showFullDescription"
            @click="showFullDescription = false"
          > [ - see less ]</a>
          <a
            v-else
            @click="showFullDescription = true"
          > [ + see more ]</a></span>
        <span v-else>{{ description }}</span>
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
  defineComponent, computed, ComputedRef, ref,
} from '@vue/composition-api';

import filesize from 'filesize';
import moment from 'moment';
import _ from 'lodash';

import store from '@/store';
import { DandisetStats } from '@/types';

// TODO: delete DandisetContributors component after redesigned contributors list is implemented
import DandisetContributors from './DandisetContributors.vue';
import ListingComponent from './ListingComponent.vue';
import ShareableLinkDialog from './ShareableLinkDialog.vue';
import ShareDialog from './ShareDialog.vue';

// max description length before it's truncated and "see more" button is shown
const MAX_DESCRIPTION_LENGTH = 400;

// TODO: remove when redesign is implemented
function renderData(data: any, schema: any): boolean {
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
  components: {
    ListingComponent,
    ShareableLinkDialog,
    ShareDialog,
    // TODO: delete DandisetContributors component after redesigned contributors list is implemented
    DandisetContributors,
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
  setup(props) {
    const { meta, schema } = props;

    const currentDandiset = computed(() => store.state.dandiset.publishDandiset);

    const stats: ComputedRef<DandisetStats|null> = computed(() => {
      if (!currentDandiset.value) {
        return null;
      }
      const { asset_count, size } = currentDandiset.value;
      return { asset_count, size };
    });

    // whether or not the "see more" button has been pressed to reveal
    // the full description
    const showFullDescription = ref(false);
    const description: ComputedRef<string> = computed(() => {
      if (!currentDandiset.value) {
        return '';
      }
      const fullDescription = currentDandiset.value.metadata?.description;
      if (!fullDescription) {
        return '';
      }
      if (fullDescription.length <= MAX_DESCRIPTION_LENGTH) {
        return fullDescription;
      }
      if (showFullDescription.value) {
        return currentDandiset.value.metadata?.description || '';
      }
      let shortenedDescription = fullDescription.substring(0, MAX_DESCRIPTION_LENGTH);
      shortenedDescription = `${shortenedDescription.substring(0, shortenedDescription.lastIndexOf(' '))}...`;
      return shortenedDescription;
    });

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
      stats,
      filesize,
      description,
      showFullDescription,
      MAX_DESCRIPTION_LENGTH,

      renderData,
      extraFields,
      schemaPropertiesCopy,
    };
  },
});
</script>
