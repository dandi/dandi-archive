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

<script>
import ObjectComponent from './Object.vue';

export default {
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
      type: [Object],
      required: true,
    },
    options: {
      type: Object,
      required: false,
      default: () => ({}),
    },
  },
};
</script>

<style>

</style>
