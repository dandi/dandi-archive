<template>
  <div
    class="full-width grey darken-2 pa-12"
  >
    <v-text-field
      label="Search Dandisets"
      outlined
      solo
      hide-details
      append-icon="mdi-magnify"
      background-color="white"
      color="black"
      data-id="search"
    />
  </div>
</template>

<script>
export default { name: 'Search' };
</script>

<style scoped>
.full-width {
  width: 100%;
}
</style>
