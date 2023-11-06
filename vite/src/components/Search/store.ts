import { reactive, ref, watch } from 'vue';
import type { Paginated, DandisetSearchResult } from '@/types';
import { DANDISETS_PER_PAGE } from '@/utils/constants';
import { dandiRest } from '@/rest';

const searchParameters = reactive<{
  file_type?: string;
  file_size_min?: number;
  file_size_max?: number;
  measurement_technique?: string[];
  genotype?: string[];
  species?: string[];
}>({});
const searchResults = ref<Paginated<DandisetSearchResult>>();
const page = ref<number>(1);
const loading = ref<boolean>(false);

async function updateSearchQuery() {
  loading.value = true;
  const results = await dandiRest.searchDandisets(
    { ...searchParameters, page_size: DANDISETS_PER_PAGE, page: page.value },
  );
  searchResults.value = results;
  loading.value = false;
}

watch(searchParameters, () => {
  page.value = 1;
  updateSearchQuery();
}, { deep: true, immediate: true });

export {
  loading,
  page,
  searchParameters,
  searchResults,
  updateSearchQuery,
};
