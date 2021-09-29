/*####################################################################################
# TODO: This is just a temporary stopgap until the contributors list is implemented  #
# as seen in the DLP redesign. This component should be removed at that point.       #
####################################################################################*/
<template>
  <div>
    <v-row
      v-if="contributors.length"
      class="mx-2"
      align="center"
    >
      <v-col>
        <span
          v-for="author in contributors"
          :key="author.name + author.identifier"
        >
          <a
            v-if="author.identifier"
            :href="'https://orcid.org/' + author.identifier"
            target="_blank"
          >
            <img
              alt="ORCID logo"
              src="https://info.orcid.org/wp-content/uploads/2019/11/orcid_16x16.png"
              width="16"
              height="16"
            ></a>
          <v-tooltip
            v-if="author.affiliation"
            top
            color="black"
          >
            <template #activator="{ on }">
              <span v-on="on">
                {{ author.name }}
              </span>
            </template>
            <span>{{ author.affiliation }}</span>
          </v-tooltip>
          <span v-else> {{ author.name }}</span>
        </span>
      </v-col>
    </v-row>
    <v-divider />
  </div>
</template>

<script lang="ts">
import { computed, ComputedRef, defineComponent } from '@vue/composition-api';

import store from '@/store';
import { DandisetContributors, Organization, Person } from '@/types/schema';

export default defineComponent({
  name: 'DandisetContributors',
  setup() {
    const contributors: ComputedRef<DandisetContributors|null> = computed(() => {
      const persons = store.state.dandiset.dandiset?.metadata?.contributor.filter((author: Person|Organization) => author.schemaKey === 'Person' && author.includeInCitation);
      if (!persons) {
        return null;
      }
      const authors: any = persons.map(
        (author: Person|Organization, index: number) => {
          let affiliations = '';
          let orcid_id = author.identifier;
          if ((author.affiliation as any)?.length) {
            affiliations = (author.affiliation as any).map((a: any) => a.name).join(', ');
          }
          let author_name = author.name;
          if (index < persons.length - 1) {
            author_name = `${author.name};`;
          }
          if (orcid_id) {
            orcid_id = `https://orcid.org/${orcid_id}`;
          }
          return { name: author_name, identifier: orcid_id, affiliation: affiliations };
        },
      );
      return authors;
    });

    return {
      contributors,
    };
  },
});
</script>
