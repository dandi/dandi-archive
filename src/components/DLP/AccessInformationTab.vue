<template>
  <div>
    <!-- TODO: implement this -->
  </div>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';

export default defineComponent({
  name: 'AccessInformationTab',
  components: {
  },
  props: {
    schema: {
      type: Object,
      required: true,
    },
    meta: {
      type: Object,
      required: true,
    },
  },
  setup() {
    return {
    };
  },
});
</script>
