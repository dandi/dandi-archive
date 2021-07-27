<template>
  <DandisetsPage
    title="Search Dandisets"
    search
  >
    <template #no-content>
      <div>
        No results!
      </div>
      <div>
        You can search by dandiset name, description, identifier, or contributor name.
      </div>
    </template>
  </DandisetsPage>
</template>

<script>
import DandisetsPage from '@/components/DandisetsPage.vue';

export default {
  name: 'SearchDandisetsView',
  components: { DandisetsPage },
};
</script>
