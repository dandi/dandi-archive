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

<script>
import DandisetsPage from '@/components/DandisetsPage.vue';

export default {
  name: 'MyDandisetsView',
  components: { DandisetsPage },
};
</script>
