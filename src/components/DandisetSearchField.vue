<template>
  <v-form @submit="performSearch">
    <v-text-field
      :value="$route.query.search"
      label="Search Dandisets by name, description, identifier, or contributor name"
      outlined
      solo
      hide-details
      :dense="dense"
      background-color="white"
      color="black"
      @input="updateSearch"
    >
      <template #prepend-inner>
        <v-icon @click="performSearch">
          mdi-magnify
        </v-icon>
      </template>
    </v-text-field>
  </v-form>
</template>

<script>
export default {
  name: 'DandisetSearchField',
  props: {
    dense: {
      type: Boolean,
      required: false,
      default: true,
    },
  },
  data() {
    return {
      currentSearch: this.$route.query.search || '',
    };
  },
  methods: {
    updateSearch(search) {
      this.currentSearch = search;
    },
    performSearch() {
      const { currentSearch } = this;
      if (currentSearch === this.$route.query.search) {
        // nothing has changed, do nothing
        return;
      }
      if (this.$route.name !== 'searchDandisets') {
        this.$router.push({
          name: 'searchDandisets',
          query: {
            search: currentSearch,
          },
        });
      } else {
        this.$router.replace({
          ...this.$route,
          query: {
            ...this.$route.query,
            search: currentSearch,
          },
        });
      }
    },
  },
};
</script>
