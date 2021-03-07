<template>
  <div>
    {{ data.join(', ') }}
  </div>
</template>

<script>
export default {
  props: {
    data: {
      type: Array,
      required: true,
    },
  },
};
</script>

<style>

</style>
