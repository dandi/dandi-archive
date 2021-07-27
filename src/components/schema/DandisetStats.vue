<template>
  <div>
    <object-component
      :data="data"
      :options="options"
      :schema="resolvedSchema"
      class="ml-5"
    />
  </div>
</template>

<script lang="ts">
import { defineComponent, PropType } from '@vue/composition-api';
import ObjectComponent from './Object.vue';
import type { RenderOptions } from './types';

export default defineComponent({
  name: 'DandisetStats',
  components: {
    ObjectComponent,
  },
  props: {
    data: {
      // The data at the matching level of schema
      type: Object,
      required: true,
    },
    schema: {
      // The root schema of the item to render
      type: Object,
      required: true,
    },
    options: {
      type: Object as PropType<RenderOptions>,
      required: false,
      default: () => ({} as RenderOptions),
    },
  },
});
</script>

<style>

</style>
