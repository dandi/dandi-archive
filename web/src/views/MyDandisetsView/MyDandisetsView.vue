<template>
  <DandisetsPage
    title="My Dandisets"
    user
  >
    <template #no-content>
      <div>
        You haven't created any dandisets yet
      </div>
    </template>
  </DandisetsPage>
</template>

<script lang="ts">
import DandisetsPage from '@/components/DandisetsPage.vue';
import { defineComponent } from '@vue/composition-api';

export default defineComponent({
  name: 'MyDandisetsView',
  components: { DandisetsPage },
});
</script>
