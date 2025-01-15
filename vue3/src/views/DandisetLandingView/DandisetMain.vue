<template>
  <div v-if="currentDandiset && meta && stats">
    <v-card
      class="px-3"
      color="grey lighten-5"
      outlined
    >
      <v-row class="mx-2 my-2 mb-0">
        <v-col
          class="d-flex align-center"
        >
          <h1 :class="`font-weight-light ${isXsDisplay ? 'text-h6' : ''}`">
            <ShareDialog />
            {{ meta.name }}
          </h1>
          <StarButton
            :identifier="currentDandiset.dandiset.identifier"
            :initial-star-count="currentDandiset.dandiset.star_count"
            :initial-is-starred="currentDandiset.dandiset.is_starred"
            class="ml-2"
          />
          <v-chip
            v-if="currentDandiset.version != 'draft'"
            outlined
            class="mx-2 pl-1"
          >
            <v-tooltip
              top
            >
              <template #activator="{ on, attrs }">
                <v-btn
                  v-if="currentDandiset !== null"
                  icon
                  small
                  v-bind="attrs"
                  v-on="on"
                  @click="copy('DOI')"
                >
                  <v-icon
                    small
                  >
                    mdi-content-copy
                  </v-icon>
                </v-btn>
              </template>
              <span>Copy DOI URL to clipboard</span>
            </v-tooltip>
            <span>
              DOI:
            </span>
            <v-divider
              vertical
              class="mx-2"
            />
            {{ meta.doi }}
          </v-chip>
        </v-col>
      </v-row>
      <v-row class="mx-1">
        <v-col :cols="isXsDisplay ? 12 : 3">
          <v-chip
            class="text-wrap py-1 pl-1"
            style="text-align: center;"
            outlined
          >
            <v-tooltip
              top
            >
              <template #activator="{ on, attrs }">
                <v-btn
                  v-if="currentDandiset !== null"
                  icon
                  small
                  v-bind="attrs"
                  v-on="on"
                  @click="copy('dandiID')"
                >
                  <v-icon
                    small
                  >
                    mdi-content-copy
                  </v-icon>
                </v-btn>
              </template>
              <span>Copy ID to clipboard</span>
            </v-tooltip>
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
        <v-col :cols="isXsDisplay ? 12 : 3">
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
        <v-col :cols="isXsDisplay ? 12 : 3">
          <span>
            <v-icon class="grey--text text--lighten-1">mdi-file</v-icon>
            File Count <strong>{{ stats.asset_count }}</strong>
          </span>
        </v-col>
        <v-col :cols="isXsDisplay ? 12 : 3">
          <span>
            <v-icon class="grey--text text--lighten-1">mdi-server</v-icon>
            Size <strong>{{ transformFilesize(stats.size) }}</strong>
          </span>
        </v-col>
      </v-row>
      <v-row
        class="mx-1"
      >
        <v-col :cols="isXsDisplay ? 12 : 3">
          <span>
            <v-icon class="grey--text text--lighten-1">mdi-calendar-range</v-icon>
            Created <strong>{{ formatDate(currentDandiset.created) }}</strong>
          </span>
        </v-col>
        <v-col :cols="isXsDisplay ? 12 : 3">
          <span>
            <v-icon class="grey--text text--lighten-1">mdi-history</v-icon>
            Last update <strong>{{ formatDate(currentDandiset.modified) }}</strong>
          </span>
        </v-col>
        <v-col :cols="isXsDisplay ? 12 : 3">
          <span v-if="meta && meta.license">
            <v-icon class="grey--text text--lighten-1">mdi-gavel</v-icon>
            Licenses:
            <strong v-if="!meta.license.length">(none)</strong>
            <span
              v-for="(license, i) in meta.license"
              :key="i"
            >
              <strong>{{ license }}</strong>
              <span v-text="meta && i === meta.license.length - 1 ? '' : ', '" />
            </span>
          </span>
        </v-col>
        <v-col :cols="isXsDisplay ? 12 : 3">
          <span v-if="accessInformation && accessInformation.length">
            <v-icon class="grey--text text--lighten-1">mdi-account-question</v-icon>
            Access Information:
            <span
              v-for="(item, i) in accessInformation"
              :key="i"
            >
              <strong>{{ item.status }}</strong>
              <span v-text="accessInformation && i === accessInformation.length - 1 ? '' : ', '" />
            </span>
          </span>
        </v-col>
      </v-row>

      <v-divider />

      <v-row class="mx-1 my-4 px-4 font-weight-light">
        <!-- We use DOMPurify to sanitize against XSS -->
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div v-html="htmlDescription" />

        <!-- Truncate text if necessary -->
        <a
          v-if="meta.description && (meta.description.length > MAX_DESCRIPTION_LENGTH)"
          @click="showFullDescription = !showFullDescription"
        > {{ showFullDescription ? "[ - see less ]" : "[ + see more ]" }}</a>
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
            <v-card-text
              v-if="subjectMatter && subjectMatter.length"
              style="border-bottom: thin solid rgba(0, 0, 0, 0.12);"
            >
              Subject matter:
              <v-chip
                v-for="(item, i) in subjectMatter"
                :key="i"
                small
                style="margin: 5px;"
              >
                {{ item.name }}
              </v-chip>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- TODO: Re-enable these tab components when the others are complete -->

      <!-- <v-tabs
        v-model="currentTab"
        background-color="grey lighten-5"
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
      </v-tabs> -->
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
import type { ComputedRef } from 'vue';
import {
  defineComponent, computed, ref,
} from 'vue';

import { filesize } from 'filesize';
import { marked } from 'marked';
import moment from 'moment';
import DOMPurify from 'dompurify';
import { useDisplay } from 'vuetify';

import { useDandisetStore } from '@/stores/dandiset';
import type { AccessInformation, DandisetStats, SubjectMatterOfTheDataset } from '@/types';

import AccessInformationTab from '@/components/DLP/AccessInformationTab.vue';
import AssetSummaryTab from '@/components/DLP/AssetSummaryTab.vue';
import ContributorsTab from '@/components/DLP/ContributorsTab.vue';
import OverviewTab from '@/components/DLP/OverviewTab.vue';
import RelatedResourcesTab from '@/components/DLP/RelatedResourcesTab.vue';
import SubjectMatterTab from '@/components/DLP/SubjectMatterTab.vue';
import ShareDialog from './ShareDialog.vue';
import StarButton from '@/components/StarButton.vue';

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
    ShareDialog,
    AccessInformationTab,
    AssetSummaryTab,
    ContributorsTab,
    OverviewTab,
    RelatedResourcesTab,
    SubjectMatterTab,
    StarButton,
  },
  props: {
    schema: {
      type: Object,
      required: true,
    },
  },
  setup() {
    const store = useDandisetStore();
    const display = useDisplay();
    
    const currentDandiset = computed(() => store.dandiset);
    const isXsDisplay = computed(() => display.xs.value);

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
    const htmlDescription: ComputedRef<string> = computed(
      () => DOMPurify.sanitize(marked.parse(description.value)),
    );
    const meta = computed(() => currentDandiset.value?.metadata);

    const accessInformation: ComputedRef<AccessInformation|undefined> = computed(
      () => meta.value?.access,
    );
    const subjectMatter: ComputedRef<SubjectMatterOfTheDataset|undefined> = computed(
      () => meta.value?.about,
    );

    const currentTab = ref(0);

    function formatDate(date: string): string {
      return moment(date).format('LL');
    }
    function copy(value:string) {
      if (!meta.value) {
        throw new Error('metadata is undefined!');
      }
      const version = meta.value?.version === 'draft' ? meta.value?.identifier as string : meta.value?.id as string;
      navigator.clipboard.writeText(value === 'dandiID' ? version : `https://doi.org/${meta.value?.doi}`);
    }

    return {
      currentDandiset,
      isXsDisplay,
      formatDate,
      stats,
      transformFilesize,
      description,
      htmlDescription,
      showFullDescription,
      MAX_DESCRIPTION_LENGTH,

      accessInformation,
      subjectMatter,
      copy,

      currentTab,
      tabs,
      meta,
    };
  },
});
</script>
