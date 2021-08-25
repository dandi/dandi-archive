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
            <ShareDialog />
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
            <template
              v-if="!currentDandiset.contact_person"
            >
              No contact information
            </template>
            <template v-else>
              Contact <strong>{{ currentDandiset.contact_person }}</strong>
            </template>
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
            File Size <strong>{{ transformFilesize(stats.size) }}</strong>
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
              v-if="meta.keywords && meta.keywords.length"
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

            <v-card-text v-if="meta.license && meta.license.length">
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

      <v-tabs
        v-model="currentTab"
        class="ml-3"
        show-arrows
      >
        <v-tabs-slider />

        <v-tab
          v-for="(tab, index) in tabs"
          :key="tab.name"
          :href="`#${index}`"
        >
          <v-icon>{{ tab.icon }}</v-icon>
          {{ tab.name }}
        </v-tab>
      </v-tabs>
    </v-card>

    <!-- Dynamically render component based on current tab -->
    <v-row class="justify-center">
      <v-col cols="11">
        <component
          :is="tabs[currentTab].component"
          v-if="tabs[currentTab]"
          v-bind="{ schema, meta }"
        />
      </v-col>
    </v-row>
  </div>
</template>

<script lang="ts">
import {
  defineComponent, computed, ComputedRef, ref,
} from '@vue/composition-api';

import filesize from 'filesize';
import moment from 'moment';

import store from '@/store';
import { DandisetStats } from '@/types';

// TODO: delete DandisetContributors component after redesigned contributors list is implemented

import AccessInformationTab from '@/components/DLP/AccessInformationTab.vue';
import AssetSummaryTab from '@/components/DLP/AssetSummaryTab.vue';
import ContributorsTab from '@/components/DLP/ContributorsTab.vue';
import OverviewTab from '@/components/DLP/OverviewTab.vue';
import RelatedResourcesTab from '@/components/DLP/RelatedResourcesTab.vue';
import SubjectMatterTab from '@/components/DLP/SubjectMatterTab.vue';
import ShareDialog from './ShareDialog.vue';
import ListingComponent from './ListingComponent.vue';
import DandisetContributors from './DandisetContributors.vue';

// max description length before it's truncated and "see more" button is shown
const MAX_DESCRIPTION_LENGTH = 400;

const tabs = [
  {
    name: 'Overview',
    component: OverviewTab,
  },
  {
    name: 'Contributors',
    component: ContributorsTab,
    icon: 'mdi-account',
  },
  {
    name: 'Subject Matter',
    component: SubjectMatterTab,
    icon: 'mdi-notebook-outline',
  },
  {
    name: 'Access Information',
    component: AccessInformationTab,
    icon: 'mdi-account-question',
  },
  {
    name: 'Asset Summary',
    component: AssetSummaryTab,
    icon: 'mdi-clipboard-list',
  },
  {
    name: 'Related Resources',
    component: RelatedResourcesTab,
    icon: 'mdi-book',
  },
];

export default defineComponent({
  name: 'DandisetMain',
  components: {
    ListingComponent,
    ShareDialog,
    // TODO: delete DandisetContributors component after redesigned contributors list is implemented
    DandisetContributors,
    AccessInformationTab,
    AssetSummaryTab,
    ContributorsTab,
    OverviewTab,
    RelatedResourcesTab,
    SubjectMatterTab,
  },
  props: {
    schema: {
      type: Object,
      required: true,
    },
  },
  setup() {
    const currentDandiset = computed(() => store.state.dandiset.dandiset);

    const transformFilesize = (size: number) => filesize(size, { round: 1, base: 10, standard: 'iec' });

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
    const meta = computed(() => currentDandiset.value?.metadata);

    const currentTab = ref('');

    function formatDate(date: string): string {
      return moment(date).format('LL');
    }

    return {
      currentDandiset,
      formatDate,
      stats,
      transformFilesize,
      description,
      showFullDescription,
      MAX_DESCRIPTION_LENGTH,

      currentTab,
      tabs,
      meta,
    };
  },
});
</script>
