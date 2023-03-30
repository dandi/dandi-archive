import { reactive, ref, watch } from 'vue';
import qs from 'querystring';
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
const loading = ref<boolean>(false);

watch(searchParameters, async (newParameters) => {
  loading.value = true;
  const { data } = await dandiRest.client.get('/search/assets', { params: { ...newParameters }, paramsSerializer: (params) => qs.stringify(params) });
  loading.value = false;
  searchResults.value = data;
}, { deep: true });

export {
  loading,
  searchParameters,
  searchResults,
};
