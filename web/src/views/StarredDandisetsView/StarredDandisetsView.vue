<template>
  <DandisetsPage
    title="Starred Dandisets"
    :dandisets="dandisets"
    :loading="loading"
    :total="total"
    :page="page"
    :page-size="pageSize"
    @page-change="handlePageChange"
  >
    <template #empty>
      <v-alert
        type="info"
        text
      >
        You haven't starred any Dandisets yet.
      </v-alert>
    </template>
  </DandisetsPage>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted } from 'vue';
import { useRoute } from 'vue-router/composables';
import DandisetsPage from '@/components/DandisetsPage.vue';
import { dandiRest } from '@/rest';
import type { Version } from '@/types';
import { DANDISETS_PER_PAGE } from '@/utils/constants';

export default defineComponent({
  name: 'StarredDandisetsView',
  components: {
    DandisetsPage,
  },
  setup() {
    const route = useRoute();
    const dandisets = ref<Version[]>([]);
    const loading = ref(true);
    const total = ref(0);
    const page = ref(Number(route.query.page || 1));
    const pageSize = ref(DANDISETS_PER_PAGE);

    async function fetchDandisets() {
      loading.value = true;
      try {
        const { data } = await dandiRest.getStarredDandisets({
          page: page.value,
          page_size: pageSize.value,
        });
        dandisets.value = data.results;
        total.value = data.count;
      } catch (error) {
        console.error('Error fetching starred Dandisets:', error);
      } finally {
        loading.value = false;
      }
    }

    function handlePageChange(newPage: number) {
      page.value = newPage;
      fetchDandisets();
    }

    onMounted(() => {
      fetchDandisets();
    });

    return {
      dandisets,
      loading,
      total,
      page,
      pageSize,
      handlePageChange,
    };
  },
});
</script> 