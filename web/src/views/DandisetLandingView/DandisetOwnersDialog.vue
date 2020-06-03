<!-- TODO: Find way to clear v-autocomplete once selected-->
<template>
  <v-card class="flex-grow-0">
    <v-card-title>Manage Ownership</v-card-title>
    <template v-if="!owners || !owners.length">
      <v-row
        align="center"
        justify="center"
        class="mx-1"
      >
        No owners
      </v-row>
    </template>
    <template v-else>
      <v-row class="mx-1 px-6">
        <v-autocomplete
          v-model="selection"
          :items="items"
          :loading="loadingUsers"
          :search-input.sync="search"
          hide-no-data
          clearable
          auto-select-first
          item-text="result"
          placeholder="Search by name or username"
          outlined
          flat
          return-object
          @update:search-input="throttledUpdate"
        />
      </v-row>
      <v-row class="mx-1">
        <v-list
          width="100%"
          style="overflow-y: auto;"
          class="px-6"
          max-height="50vh"
        >
          <template
            v-for="(owner, i) in newOwners"
          >
            <v-list-item
              :key="owner._id"
            >
              <v-list-item-title>
                {{ owner.name }} ({{ owner.login }})
              </v-list-item-title>
              <v-list-item-action>
                <v-btn
                  icon
                  @click="removeOwner(i)"
                >
                  <v-icon>mdi-close</v-icon>
                </v-btn>
              </v-list-item-action>
            </v-list-item>
            <v-divider :key="`${owner.id}-divider`" />
          </template>
        </v-list>
      </v-row>
    </template>
    <v-row
      justify="end"
      align="end"
      class="mx-1 pt-4 pb-2"
    >
      <v-btn
        tile
        text
        @click="close"
      >
        Cancel
      </v-btn>
      <v-btn
        tile
        text
        color="primary"
        @click="save"
      >
        Save Changes
      </v-btn>
    </v-row>
  </v-card>
</template>

<script>
import girderRest, { user } from '@/rest';
import { mapState, mapMutations } from 'vuex';
import _ from 'lodash';


const userFormatConversion = (users) => users.map(({
  _id, _accessLevel, login, firstName, lastName,
}) => ({
  id: _id, level: _accessLevel, login, name: `${firstName} ${lastName}`,
}));

const addResult = (users) => users.map((u) => ({ ...u, result: `${u.name} (${u.login})` }));

export default {
  name: 'DandisetOwnersDialog',
  props: {
    owners: {
      type: Array,
      required: true,
    },
  },
  data() {
    return {
      search: null,
      loadingUsers: false,
      selection: null,
      newOwners: addResult(this.owners),
      items: [],
      throttledUpdate: _.debounce(this.updateItems, 200),
    };
  },
  computed: {
    user,
    ...mapState('girder', ['currentDandiset']),
  },
  watch: {
    selection(val) {
      if (!val || this.newOwners.find((x) => x.id === val.id)) return;
      this.newOwners.push(val);
    },
  },
  methods: {
    async updateItems() {
      if (!this.search) return;

      this.loadingUsers = true;
      const { data } = await girderRest.get('/user/', { params: { text: this.search } });

      // Needed to match existing owner document schema
      this.items = addResult(userFormatConversion(data));

      this.loadingUsers = false;
    },
    removeOwner(index) {
      this.newOwners.splice(index, 1);
    },
    close() {
      this.$emit('close');
    },
    async save() {
      const { identifier } = this.currentDandiset.meta.dandiset;
      const formattedOwners = this.newOwners.map((owner) => ({ _id: owner.id }));

      const { data } = await girderRest.put(`/dandi/${identifier}/owners`, formattedOwners);
      this.setCurrentDandisetOwners(data);
      this.close();
    },
    ...mapMutations('girder', ['setCurrentDandisetOwners']),
  },
};
</script>
