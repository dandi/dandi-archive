<template>
  <div>
    <v-card outlined>
      <v-card-title>
        <v-icon class="mr-3">
          mdi-account-multiple
        </v-icon>
        Contributors
      </v-card-title>
      <v-chip
        v-for="(contributor, i) in contributors"
        :key="i"
        style="margin: 5px;"
        outlined
      >
        {{ contributor.name }}
      </v-chip>
    </v-card>

    <v-row>
      <v-col cols="4">
        <v-card outlined>
          <v-card-title>
            <v-icon class="mr-3">
              mdi-notebook-outline
            </v-icon>
            Subject matter
          </v-card-title>

          <v-list>
            <v-list-item
              v-for="(item, i) in subjectMatter"
              :key="i"
            >
              {{ item.name }}
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>

      <v-col cols="4">
        <v-card outlined>
          <v-card-title>
            <v-icon class="mr-3">
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
          <v-card-title>
            <v-icon class="mr-3">
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
  DandisetContributors,
  DandisetMetadata,
  RelatedResource,
  SubjectMatterOfTheDataset,
} from '@/types';
import {
  computed,
  ComputedRef,
  defineComponent, PropType,
} from '@vue/composition-api';

export default defineComponent({
  name: 'OverviewTab',
  components: {
  },
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
    const contributors: ComputedRef<DandisetContributors> = computed(() => props.meta.contributor);
    const subjectMatter: ComputedRef<SubjectMatterOfTheDataset|undefined> = computed(
      () => props.meta.about,
    );
    const accessInformation: ComputedRef<AccessInformation|undefined> = computed(
      () => props.meta.access,
    );
    const relatedResources: ComputedRef<RelatedResource|undefined> = computed(
      () => props.meta.relatedResource,
    );

    return {
      contributors,
      subjectMatter,
      accessInformation,
      relatedResources,
    };
  },
});
</script>
