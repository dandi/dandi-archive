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
              {{ item.status }}
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
              {{ item.url }}
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>
    </v-row>
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
        (contributor) => !!(contributor.includeInCitation),
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

    const contactPeople = computed(
      () => new Set(contributors.value
        .filter((contributor) => contributor.roleName?.includes('dcite:ContactPerson'))
        .map((contributor) => contributor.name)),
    );

    return {
      contributors,
      subjectMatter,
      accessInformation,
      relatedResources,
      contactPeople,
    };
  },
});
</script>
