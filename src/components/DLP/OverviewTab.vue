<template>
  <div>
    <v-card outlined>
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
          close-icon="mdi-card-account-mail"
          :close="contactPeople.has(contributor.name)"
        >
          {{ contributor.name }}
          <a
            v-if="contributor.identifier"
            :href="`https://orcid.org/${contributor.identifier}`"
            target="_blank"
            class="mx-1"
          >
            <img
              alt="ORCID logo"
              src="https://info.orcid.org/wp-content/uploads/2019/11/orcid_16x16.png"
              width="16"
              height="16"
            >
          </a>
        </v-chip>
      </div>
    </v-card>

    <v-card
      outlined
      class="mt-3"
    >
      <v-card-title class="font-weight-regular">
        <v-icon class="mr-3 grey--text text--lighten-1">
          mdi-currency-usd
        </v-icon>
        Funding information
      </v-card-title>

      <v-list
        class="pl-4"
        :style="`column-count: ${Math.min(Math.ceil(fundingInformation.length / 2), 4)};`"
      >
        <div
          v-for="(item, i) in fundingInformation"
          :key="i"
          class="my-2"
        >
          <div
            class="d-inline-block"
            style="width: 100%;"
          >
            <MetadataListItem>
              <v-row
                no-gutters
                class="justify-space-between"
              >
                <v-col
                  cols="9"
                  class="grey--text text--darken-3"
                >
                  <div class="mb-1">
                    {{ item.name }}
                  </div>
                  <div
                    v-if="item.awardNumber"
                    class="text-caption grey--text text--darken-1"
                  >
                    <strong>Award Number: </strong>{{ item.awardNumber }}
                  </div>
                  <div
                    v-if="item.roleName && item.roleName.length"
                    class="text-caption grey--text text--darken-1"
                  >
                    <strong>Roles: </strong>
                    <div
                      v-for="(role, ii) in item.roleName"
                      :key="ii"
                      class="ml-4"
                    >
                      - {{ role }}
                    </div>
                  </div>
                  <div
                    v-if="item.contactPoint && item.contactPoint.length"
                    class="text-caption grey--text text--darken-1"
                  >
                    <strong>Contact points: </strong>
                    <div
                      v-for="(contact, ii) in item.contactPoint"
                      :key="ii"
                      class="ml-4"
                    >
                      <span>
                        -
                        <a :href="`mailto:${contact.email}`">{{ contact.email }}</a>
                        /
                        <a :href="contact.url">{{ contact.url }}</a>
                      </span>
                    </div>
                  </div>
                </v-col>
                <v-col
                  v-if="item.url"
                  class="pl-1 text-end font-weight-light"
                >
                  <v-btn
                    icon
                    :href="item.url"
                    target="_blank"
                    rel="noopener"
                  >
                    <v-icon>mdi-link</v-icon>
                  </v-btn>
                </v-col>
              </v-row>
            </MetadataListItem>
          </div>
        </div>
      </v-list>
    </v-card>

    <v-row>
      <v-col cols="4">
        <v-card outlined>
          <v-card-title class="font-weight-regular">
            <v-icon class="mr-3 grey--text text--lighten-1">
              mdi-notebook-outline
            </v-icon>
            Subject matter
          </v-card-title>

          <v-list>
            <v-list-item
              v-for="(item, i) in subjectMatter"
              :key="i"
            >
              <MetadataListItem>
                <v-row
                  no-gutters
                  class="justify-space-between"
                >
                  <v-col
                    cols="6"
                    class="grey--text text--darken-3"
                  >
                    {{ item.name }}
                  </v-col>
                  <v-col
                    cols="6"
                    class="pl-1 text-end font-weight-light"
                  >
                    {{ item.identifier }}
                  </v-col>
                </v-row>
                <span class="text-caption grey--text text--darken-1">
                  {{ item.schemaKey.toUpperCase() }}
                </span>
              </MetadataListItem>
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>

      <v-col cols="4">
        <v-card outlined>
          <v-card-title class="font-weight-regular">
            <v-icon class="mr-3 grey--text text--lighten-1">
              mdi-account-question
            </v-icon>
            Access Information
          </v-card-title>

          <v-list>
            <v-list-item
              v-for="(item, i) in accessInformation"
              :key="i"
            >
              <MetadataListItem>
                <v-row
                  no-gutters
                  class="justify-space-between"
                >
                  <v-col
                    cols="9"
                    class="grey--text text--darken-3"
                  >
                    {{ item.description }}
                    <br>
                    <span class="text-caption grey--text text--darken-1">
                      {{ item.status }}
                    </span>
                  </v-col>
                  <v-col
                    v-if="item.contactPoint"
                    class="pl-1 text-end font-weight-light"
                  >
                    <v-btn
                      v-if="item.contactPoint.url"
                      icon
                      :href="item.contactPoint.url"
                      target="_blank"
                      rel="noopener"
                    >
                      <v-icon>mdi-link</v-icon>
                    </v-btn>
                    <v-btn
                      v-if="item.contactPoint.email"
                      icon
                      :href="`mailto:${item.contactPoint.email}`"
                      target="_blank"
                      rel="noopener"
                    >
                      <v-icon>mdi-email</v-icon>
                    </v-btn>
                  </v-col>
                </v-row>
              </MetadataListItem>
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>

      <v-col cols="4">
        <v-card outlined>
          <v-card-title class="font-weight-regular">
            <v-icon class="mr-3 grey--text text--lighten-1">
              mdi-book
            </v-icon>
            Related resources
          </v-card-title>

          <v-list>
            <v-list-item
              v-for="(item, i) in relatedResources"
              :key="i"
            >
              <MetadataListItem>
                <v-row
                  no-gutters
                  class="justify-space-between"
                >
                  <v-col
                    cols="9"
                    class="grey--text text--darken-3"
                  >
                    {{ item.name }}
                    <br>
                    <span
                      class="text-caption grey--text text--darken-1 related-resource"
                    >
                      <span>ID: </span>{{ item.identifier }}
                    </span>
                    <br>
                    <span class="text-caption grey--text text--darken-1">
                      <span>Repo: </span>{{ item.repository }}
                    </span>
                    <br>
                    <span class="text-caption grey--text text--darken-1">
                      <span>Relation: </span>{{ item.relation }}
                    </span>
                  </v-col>
                  <v-col
                    v-if="item.url"
                    class="pl-1 text-end font-weight-light"
                  >
                    <v-btn
                      icon
                      :href="item.url"
                      target="_blank"
                      rel="noopener"
                    >
                      <v-icon>mdi-link</v-icon>
                    </v-btn>
                  </v-col>
                </v-row>
              </MetadataListItem>
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>
    </v-row>

    <v-card
      outlined
    >
      <v-card-title class="font-weight-regular">
        <v-icon class="mr-3 grey--text text--lighten-1">
          mdi-clipboard-list
        </v-icon>
        Asset Summary
      </v-card-title>
      <v-list
        style="column-count: 3;"
        class="px-3"
      >
        <div
          v-for="([type, items], i) in Object.entries(assetSummary)"
          :key="i"
        >
          <div
            class="d-inline-block"
            style="width: 100%;"
          >
            <span class="font-weight-bold">
              {{ type }}
            </span>
            <MetadataListItem
              v-for="(item, ii) in items"
              :key="ii"
              :title="type"
              background-color="grey lighten-4"
            >
              <v-row
                no-gutters
                class="align-center py-0"
                style="min-height: 2em;"
              >
                <v-col
                  cols="10"
                >
                  <span>{{ item.name || item }}</span>
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
            </MetadataListItem>
          </div>
        </div>
      </v-list>
    </v-card>
  </div>
</template>

<script lang="ts">
import {
  AccessInformation,
  DandisetMetadata,
  RelatedResource,
  SubjectMatterOfTheDataset,
} from '@/types';
import {
  computed,
  ComputedRef,
  defineComponent, PropType,
} from '@vue/composition-api';

import MetadataListItem from '@/components/DLP/MetadataListItem.vue';

const ASSET_SUMMARY_BLACKLIST = new Set([
  'numberOfBytes',
  'numberOfFiles',
  'numberOfSubjects',
  'numberOfSamples',
  'numberOfCells',
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
  components: { MetadataListItem },
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
    const contributors = computed(
      () => props.meta.contributor.filter(
        (contributor) => !!(contributor.includeInCitation) && !!(contributor.schemaKey === 'Person'),
      ),
    );
    const fundingInformation = computed(
      () => props.meta.contributor?.filter(
        (contributor) => !!(contributor.schemaKey === 'Organization')
        // Only include organizations with "Sponsor" or "Funder" roles in Funding Information
        && (contributor.roleName?.includes('dcite:Funder') || contributor.roleName?.includes('dcite:Sponsor')),
      ),
    );

    const subjectMatter: ComputedRef<SubjectMatterOfTheDataset|undefined> = computed(
      () => props.meta.about,
    );
    const accessInformation: ComputedRef<AccessInformation|undefined> = computed(
      () => props.meta.access,
    );
    const relatedResources: ComputedRef<RelatedResource|undefined> = computed(
      () => props.meta.relatedResource,
    );
    const assetSummary = computed(
      () => Object.fromEntries(Object.entries(props.meta.assetsSummary).filter(
        // filter out assetSummary fields we don't want to display
        ([key]) => !ASSET_SUMMARY_BLACKLIST.has(key),
      ).map(
        // convert from camelCase to space-delimited string (i.e. "dataStandard" to "data Standard")
        ([key, value]) => [key.replace(/[A-Z]/g, (letter) => ` ${letter.toUpperCase()}`), value],
      ).map(
        // capitalize the first letter in the string
        ([key, value]: any) => [key.charAt(0).toUpperCase() + key.slice(1), value],
      )),
    );

    const contactPeople = computed(
      () => new Set(contributors.value
        .filter((contributor) => contributor.roleName?.includes('dcite:ContactPerson'))
        .map((contributor) => contributor.name)),
    );

    return {
      contributors,
      fundingInformation,
      subjectMatter,
      accessInformation,
      relatedResources,
      assetSummary,
      contactPeople,
      isURL,
    };
  },
});
</script>
