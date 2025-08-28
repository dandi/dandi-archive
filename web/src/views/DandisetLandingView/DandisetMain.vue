<template>
  <div v-if="currentDandiset && meta && stats">
    <v-card
      class="border-b pa-10"
      color="grey-lighten-5"
      style="box-shadow:0 0 16px rgba(0, 0, 0, .2)"
      flat
      tile
    >
      <v-row>
        <v-col
          class="d-flex align-start justify-space-between py-0"
        >
          <div class="title-container d-flex align-center">
            <h1 :class="`font-weight-light ${isXsDisplay ? 'text-h6' : ''}`">
              <ShareDialog />
              {{ meta.name }}
            </h1>
          </div>
          <StarButton
            :identifier="currentDandiset.dandiset.identifier"
            :initial-star-count="currentDandiset.dandiset.star_count"
            :initial-is-starred="currentDandiset.dandiset.is_starred"
            class="ml-2"
          />
          <v-chip
            v-if="meta.doi"
            variant="outlined"
            class="mx-2 pl-1"
          >
            <v-tooltip location="top">
              <template #activator="{ props }">
                <v-btn
                  v-if="currentDandiset !== null"
                  icon
                  size="small"

                  v-bind="props"
                  @click="copy('DOI')"
                >
                  <v-icon
                    size="small"
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
      <v-row>
        <v-col :cols="isXsDisplay ? 12 : 3">
          <v-chip
            class="text-wrap py-1 pl-1"
            style="text-align: center;"
            variant="outlined"
          >
            <v-tooltip
              location="top"
            >
              <template #activator="{ props }">
                <v-btn
                  v-if="currentDandiset !== null"
                  icon
                  size="small"
                  variant="plain"
                  v-bind="props"
                  @click="copy('dandiID')"
                >
                  <v-icon
                    size="small"
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
            <v-icon class="text-grey-lighten-1">mdi-account</v-icon>
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
            <v-icon class="text-grey-lighten-1">mdi-file</v-icon>
            File Count <strong>{{ stats.asset_count }}</strong>
          </span>
        </v-col>
        <v-col :cols="isXsDisplay ? 12 : 3">
          <span>
            <v-icon class="text-grey-lighten-1">mdi-server</v-icon>
            Size <strong>{{ transformFilesize(stats.size) }}</strong>
          </span>
        </v-col>
      </v-row>
      <v-row>
        <v-col :cols="isXsDisplay ? 12 : 3">
          <span>
            <v-icon class="text-grey-lighten-1">mdi-calendar-range</v-icon>
            Created <strong>{{ formatDate(currentDandiset.created) }}</strong>
          </span>
        </v-col>
        <v-col :cols="isXsDisplay ? 12 : 3">
          <span>
            <v-icon class="text-grey-lighten-1">mdi-history</v-icon>
            Last update <strong>{{ formatDate(currentDandiset.modified) }}</strong>
          </span>
        </v-col>
        <v-col :cols="isXsDisplay ? 12 : 3">
          <span v-if="meta && meta.license">
            <v-icon class="text-grey-lighten-1">mdi-gavel</v-icon>
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
            <v-icon class="text-grey-lighten-1">mdi-account-question</v-icon>
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
        <v-divider class="ma-3" />
      </v-row>

      <v-row class="font-weight-light">
        <v-col>
          <!-- We use DOMPurify to sanitize against XSS -->
          <!-- eslint-disable-next-line vue/no-v-html -->
          <div v-html="htmlDescription" />

          <!-- Truncate text if necessary -->
          <a
            v-if="meta.description && (meta.description.length > MAX_DESCRIPTION_LENGTH)"
            @click="showFullDescription = !showFullDescription"
          > {{ showFullDescription ? "[ - see less ]" : "[ + see more ]" }}</a>
        </v-col>
      </v-row>

      <v-row class="justify-center">
        <v-col
          cols="12"
          class="pb-0"
        >
          <v-card
            v-if="(meta.keywords && meta.keywords.length) || (meta.license && meta.license.length)"
            variant="outlined"
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
                size="small"
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
                size="small"
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
      <v-col cols="12">
        <component
          :is="tabs[currentTab].component"
          v-if="tabs[currentTab]"
          v-bind="{ schema, meta }"
          class="d-flex flex-column pa-9 ga-3 w-100"
        />
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
import {
  computed,
  ref,
  watchEffect,
  type ComputedRef,
} from 'vue';

import { filesize } from 'filesize';
import { marked } from 'marked';
import moment from 'moment';
import DOMPurify from 'dompurify';
import { useDisplay } from 'vuetify';

import { useDandisetStore } from '@/stores/dandiset';
import { getDoiMetadata } from '@/utils/doi';
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

defineProps({
  schema: {
    type: Object,
    required: true,
  },
});

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
  () => DOMPurify.sanitize(marked.parse(description.value) as string),
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

watchEffect(async () => {
  // Inject datacite metadata into the page
  if (meta.value?.doi) {
    const metadataText = await getDoiMetadata(meta.value.doi as string);
    const script = document.createElement('script');
    script.setAttribute('type', 'application/ld+json');
    script.textContent = metadataText;
    document.head.appendChild(script);
  }
});
</script>
