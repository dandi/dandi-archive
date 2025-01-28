<script setup lang="ts">
import { type ComputedRef, computed } from 'vue';
import DandisetList from '@/components/DandisetList.vue';
import { omit } from 'lodash';
import type { Version } from '@/types';
import { DANDISETS_PER_PAGE } from '@/utils/constants';
import {
  searchResults, loading, page, updateSearchQuery,
} from './store';

interface VersionSearchResult extends Version {
  asset_counts: Record<string, number>;
}

const SEARCH_ICONS: Record<string, string> = {
  file_type: 'mdi-file',
  measurement_technique: 'mdi-tape-measure',
  file_size: 'mdi-harddisk',
  species: 'mdi-sprout',
  genotype: 'mdi-dna',
};

const dandisets = computed(
  () => searchResults.value?.results.map((dandiset) => ({
    ...(dandiset.most_recent_published_version || dandiset.draft_version),
    dandiset: omit(dandiset, 'most_recent_published_version', 'draft_version'),
    asset_counts: dandiset.asset_counts,
  })),
) as ComputedRef<VersionSearchResult[] | undefined>;
</script>

<template>
  <v-container>
    <span class="text-h4">Results ({{ searchResults?.count || 0 }})</span>
    <v-sheet class="ma-2 pa-2">
      <v-sheet
        v-if="loading"
        height="100%"
        class="d-flex justify-center align-center"
      >
        <v-progress-circular
          :size="100"
          :width="5"
          indeterminate
        />
      </v-sheet>
      <DandisetList
        v-else-if="dandisets"
        class="mx-4 mx-md-8 my-8"
        :dandisets="dandisets"
      >
        <template
          v-for="result in dandisets"
          #[result.dandiset.identifier]
        >
          <v-sheet
            :key="result.dandiset.identifier"
            class="d-flex flex-column"
          >
            <div
              v-for="[searchParam, assetCount] in Object.entries(result.asset_counts)"
              :key="`${searchParam}:${assetCount}`"
              class="my-1"
            >
              <v-icon>{{ SEARCH_ICONS[searchParam] }}</v-icon>
              <span class="font-weight-bold">
                {{ assetCount }}
              </span>
              assets matching
              <span class="font-weight-bold">
                {{ searchParam.replaceAll('_', ' ') }}
              </span>
            </div>
          </v-sheet>
        </template>
      </DandisetList>
    </v-sheet>
    <v-pagination
      v-if="searchResults"
      v-model="page"
      :length="Math.ceil(searchResults.count / DANDISETS_PER_PAGE)"
      @update:model-value="updateSearchQuery"
    />
  </v-container>
</template>
