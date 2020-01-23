<template>
  <div>
    {{id}}
  </div>
</template>

<script>
import { mapState } from 'vuex';

export default {
  props: ['id'],
  computed: {
    ...mapState(['selected']),
  },
  components: {},
};
</script>

<style>

</style>
