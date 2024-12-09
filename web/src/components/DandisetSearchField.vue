<template>
  <v-form style="width: 100%" @submit="performSearch">
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
        <v-icon @click="performSearch"> mdi-magnify </v-icon>
      </template>
    </v-text-field>
  </v-form>
</template>

<script lang="ts">
import { defineComponent, ref } from "vue";
import type { RawLocation } from "vue-router";
import { useRoute } from "vue-router/composables";
import router from "@/router";

export default defineComponent({
  name: "DandisetSearchField",
  props: {
    dense: {
      type: Boolean,
      required: false,
      default: true,
    },
  },
  setup() {
    const route = useRoute();
    const currentSearch = ref(route.query.search || "");

    function updateSearch(search: string) {
      currentSearch.value = search;
    }

    function performSearch(evt: Event) {
      evt.preventDefault(); // prevent form submission from refreshing page

      if (currentSearch.value === route.query.search) {
        // nothing has changed, do nothing
        return;
      }
      if (route.name !== "searchDandisets") {
        router.push({
          name: "searchDandisets",
          query: {
            search: currentSearch.value,
          },
        });
      } else {
        router.replace({
          ...route,
          query: {
            ...route.query,
            search: currentSearch.value,
          },
        } as RawLocation);
      }
    }

    return {
      currentSearch,
      updateSearch,
      performSearch,
    };
  },
});
</script>
