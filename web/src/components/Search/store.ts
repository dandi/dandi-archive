import { reactive, ref, watch } from 'vue';
import { dandiRest } from '@/rest';

const searchParameters = reactive<{
  file_type?: string;
  file_type_min?: number;
  file_type_max?: number;
  measurement_technique?: string[];
  genotype?: string[];
  species?: string[];
}>({});
const searchResults = ref([]);

watch(searchParameters, async (newParameters) => {
  const { data } = await dandiRest.client.get('/search/assets', { params: { ...newParameters } });
  searchResults.value = data;
}, { deep: true });

export {
  searchParameters,
  searchResults,
};
