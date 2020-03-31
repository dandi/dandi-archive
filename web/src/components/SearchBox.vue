<template>
  <v-container>
    TODO: SearchBox
    <GirderSearch
      search-mode="dandi"
      :search-types="['item']"
      :hide-options-menu="true"
      placeholder="Type search query"
      @select="selectSearchResult"
    >
      <template v-slot:searchresult="result">
        <v-list-item-action>
          <v-icon> {{ $vuetify.icons.values[result._modelType] }} </v-icon>
        </v-list-item-action>
        <v-list-item-content>
          <v-list-item-title>{{ result.name }}</v-list-item-title>
          <v-list-item-subtitle>
            {{ result.meta.institution + " " + result.meta.lab + " lab" }}
          </v-list-item-subtitle>
        </v-list-item-content>
      </template>
      <template v-slot:noresult="{ searchText }">
        <v-list-item-action>
          <v-icon>$vuetify.icons.alert</v-icon>
        </v-list-item-action>
        <v-list-item-content>
          <v-list-item-title>
            No results found for query '{{ searchText }}'
          </v-list-item-title>
          <v-list-item-subtitle>
            Please use our search grammar.
          </v-list-item-subtitle>
        </v-list-item-content>
      </template>
    </GirderSearch>
  </v-container>
</template>

<script>
import { mapActions } from 'vuex';
import { Search as GirderSearch } from '@girder/components/src/components';

export default {
  name: 'SearchBox',
  components: {
    GirderSearch,
  },
  methods: {
    ...mapActions('girder', ['selectSearchResult']),
  },
};
</script>
