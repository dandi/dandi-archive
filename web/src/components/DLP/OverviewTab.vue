<template>
  <div>
    <v-card
      v-if="contributors && contributors.length"
      outlined
      height="100%"
    >
      <v-card-title class="font-weight-regular">
        <v-icon class="mr-3 grey--text text--lighten-1">
          mdi-account-multiple
        </v-icon>
        Contributors
      </v-card-title>
      <div class="px-2 mb-2">
        <v-chip
          v-for="(contributor, i) in contributors"
          :key="i"
          style="margin: 5px;"
          outlined
        >
          {{ contributor.name }}
          <a
            v-if="contributor.identifier"
            :href="`https://orcid.org/${contributor.identifier}`"
            target="_blank"
            class="mx-1 d-flex align-center"
          >
            <img
              alt="ORCID logo"
              src="https://info.orcid.org/wp-content/uploads/2019/11/orcid_16x16.png"
              width="16"
              height="16"
            >
          </a>
          <a
            v-if="contactPeople.has(contributor.name)"
            :href="contributor.email ? `mailto:${contributor.email}` : undefined"
            class="mx-1 text-decoration-none"
          >
            <v-icon color="info">mdi-card-account-mail</v-icon>
          </a>
        </v-chip>
      </div>
    </v-card>

    <MetadataCard
      :items="fundingInformation"
      name="Funding information"
      icon="mdi-currency-usd"
    >
      <template #content="slotProps">
        <div
          class="text-caption grey--text text--darken-1"
        >
          <span
            v-if="slotProps.item.awardNumber"
            class="pl-2"
          >
            <strong>- Award Number: </strong>{{ slotProps.item.awardNumber }}
          </span>
        </div>
      </template>
      <template #emptyFallback>
        <span class="font-italic font-weight-bold">
          No funding information available.
        </span>
      </template>
    </MetadataCard>

    <MetadataCard
      v-if="relatedResources && relatedResources.length"
      :items="relatedResources"
      name="Related resources"
      icon="mdi-book"
    >
      <template #content="slotProps">
        <span
          v-if="slotProps.item.identifier"
          class="text-caption grey--text text--darken-1 related-resource"
        >
          <strong>ID: </strong>{{ slotProps.item.identifier }}
          <br>
        </span>
        <span
          v-if="slotProps.item.repository"
          class="text-caption grey--text text--darken-1"
        >
          <strong>Repo: </strong>{{ slotProps.item.repository }}
          <br>
        </span>
        <span
          v-if="slotProps.item.relation"
          class="text-caption grey--text text--darken-1"
        >
          <strong>Relation: </strong>{{ slotProps.item.relation }}
        </span>
      </template>
      <template #links="slotProps">
        <v-btn
          v-if="slotProps.item.url"
          icon
          :href="slotProps.item.url"
          target="_blank"
          rel="noopener"
        >
          <v-icon>mdi-link</v-icon>
        </v-btn>
      </template>
    </MetadataCard>

    <v-card
      v-if="assetSummary"
      outlined
    >
      <v-card-title class="font-weight-regular">
        <v-progress-circular
          v-if="assetSummaryBeingComputed"
          class="mr-3"
          size="20"
          indeterminate
        />
        <v-icon
          v-else
          class="mr-3 grey--text text--lighten-1"
        >
          mdi-clipboard-list
        </v-icon>
        Assets Summary
      </v-card-title>
      <v-list
        :style="`column-count: ${assetSummaryColumnCount};`"
        class="px-3 ml-2"
      >
        <div
          v-if="assetSummaryBeingComputed"
          class="text-subtitle-2"
        >
          The assets summary is being computed, please wait.
        </div>
        <div
          v-else-if="!assetSummary || !Object.keys(assetSummary).length"
          class="font-italic font-weight-bold"
        >
          This Dandiset does not contain any assets.
        </div>
        <div
          v-for="([type, items], i) in Object.entries(assetSummary)"
          v-else
          :key="i"
        >
          <div
            v-if="items && items.length"
            class="d-inline-block"
            style="width: 100%;"
          >
            <span class="font-weight-bold">
              {{ type }}
            </span>
            <div
              v-for="(item, ii) in items"
              :key="ii"
              :title="type"
              background-color="grey lighten-4"
              class="grey lighten-4"
              style="width: 100%;"
            >
              <div
                class="pl-2 my-1 py-1"
                :style="`border-left: medium solid ${$vuetify.theme.themes.light.primary};
                         line-height: 1.25`"
              >
                <v-row
                  no-gutters
                  class="align-center py-0"
                  style="min-height: 2em;"
                >
                  <v-col
                    cols="10"
                  >
                    <span>{{ item.name || item.identifier || item.id || item }}</span>
                  </v-col>
                  <v-col>
                    <v-btn
                      v-if="isURL(item.identifier)"
                      icon
                      :href="item.identifier"
                      target="_blank"
                      rel="noopener"
                    >
                      <v-icon>mdi-link</v-icon>
                    </v-btn>
                  </v-col>
                </v-row>
                <span
                  v-if="!isURL(item.identifier)"
                  class="text-caption grey--text text--darken-1"
                >
                  {{ item.identifier }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </v-list>
    </v-card>

    <MetadataCard
      v-if="associatedProjects && associatedProjects.length"
      :items="associatedProjects"
      name="Associated Projects"
      icon="mdi-file-document-multiple"
    >
      <template #content="slotProps">
        <span
          v-if="slotProps.item.identifier"
          class="text-caption grey--text text--darken-1 related-resource"
        >
          <strong>Identifier: </strong>{{ slotProps.item.identifier }}
          <br>
        </span>
      </template>
    </MetadataCard>
  </div>
</template>

<script lang="ts">
import { AssociatedProjects, DandisetMetadata, RelatedResource } from '@/types';
import {
  computed,
  ComputedRef,
  defineComponent, getCurrentInstance, onMounted, PropType,
} from 'vue';

import MetadataCard from '@/components/DLP/MetadataCard.vue';
import { useDandisetStore } from '@/stores/dandiset';

// Asset summary fields to hide
const ASSET_SUMMARY_BLACKLIST = new Set([
  'numberOfBytes',
  'numberOfFiles',
  'schemaKey',
]);

/**
 * Determines if the given string is a URL
 */
function isURL(str: string): boolean {
  let url;
  try {
    url = new URL(str);
  } catch (e) {
    return false;
  }

  return url.protocol === 'http:' || url.protocol === 'https:';
}

export default defineComponent({
  name: 'OverviewTab',
  components: { MetadataCard },
  props: {
    schema: {
      type: Object,
      required: true,
    },
    meta: {
      type: Object as PropType<DandisetMetadata>,
      required: true,
    },
  },
  setup(props) {
    const $vuetify = computed(() => getCurrentInstance()?.proxy.$vuetify);

    const store = useDandisetStore();
    const currentDandiset = computed(() => store.dandiset);

    const contributors = computed(
      () => props.meta.contributor?.filter(
        (contributor) => !!(contributor.includeInCitation) && !!(contributor.schemaKey === 'Person'),
      ),
    );
    const fundingInformation = computed(
      () => props.meta.contributor?.filter(
        (contributor) => !!(contributor.schemaKey === 'Organization')
        // Only include organizations with "Sponsor" or "Funder" roles in Funding Information
        && (contributor.roleName?.includes('dcite:Funder') || contributor.roleName?.includes('dcite:Sponsor')),
      ) || [],
    );

    const relatedResources: ComputedRef<RelatedResource|undefined> = computed(
      () => props.meta.relatedResource,
    );

    const associatedProjects: ComputedRef<AssociatedProjects|undefined> = computed(
      () => props.meta.wasGeneratedBy,
    );

    const assetSummary = computed<Record<string, any>>(
      () => Object.fromEntries(Object.entries(props.meta.assetsSummary).filter(
        // filter out assetSummary fields we don't want to display
        ([key, value]) => !!value && !ASSET_SUMMARY_BLACKLIST.has(key),
      ).map(
        // convert from camelCase to space-delimited string (i.e. "dataStandard" to "data Standard")
        ([key, value]) => [key.replace(/[A-Z]/g, (letter) => ` ${letter.toUpperCase()}`), value],
      ).map(
        // capitalize the first letter in the string
        ([key, value]: any) => [key.charAt(0).toUpperCase() + key.slice(1), value],
      )
        // convert primitive types to single-element arrays so they can be more easily rendered
        .map(([key, value]: any) => (typeof value === 'object' ? [key, value] : [key, [value]]))),
    );

    // Approximate a good column count for asset summary card
    const assetSummaryColumnCount = computed(
      () => ($vuetify.value?.breakpoint.mdAndDown ? 1
        : Math.min(Object.keys(assetSummary.value).length, 3)),
    );

    const assetSummaryBeingComputed = computed<boolean>(() => currentDandiset.value?.status === 'Pending');

    const contactPeople = computed(
      () => new Set(contributors.value
        .filter((contributor) => contributor.roleName?.includes('dcite:ContactPerson'))
        .map((contributor) => contributor.name)),
    );

    onMounted(() => {
      setInterval(async () => {
        if (!currentDandiset.value || !assetSummaryBeingComputed.value) {
          return;
        }
        const { identifier } = currentDandiset.value.dandiset;
        const { version } = currentDandiset.value;
        await store.fetchDandiset({ identifier, version });
      }, 5000);
    });

    return {
      contributors,
      fundingInformation,
      relatedResources,
      associatedProjects,
      assetSummary,
      assetSummaryColumnCount,
      assetSummaryBeingComputed,
      contactPeople,
      isURL,
    };
  },
});
</script>
