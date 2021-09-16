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
            :href="author.identifier"
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
import { DandisetContributors } from '@/types/schema';
import { computed, ComputedRef, defineComponent } from '@vue/composition-api';

export default defineComponent({
  name: 'DandisetContributors',
  setup(props, ctx) {
    const store = ctx.root.$store;
    const contributors: ComputedRef<DandisetContributors> = computed(
      () => store.state.dandiset.publishDandiset.metadata.contributor,
    );

    return {
      contributors,
    };
  },
});
</script>
