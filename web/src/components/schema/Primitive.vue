<template>
  <div>{{ data }}</div>
</template>

<script>
export default {
  name: 'Primitive',
  props: {
    data: {
      // The data at the matching level of schema
      type: [Number, String],
      required: true,
    },
  },
};
</script>

<style>

</style>
