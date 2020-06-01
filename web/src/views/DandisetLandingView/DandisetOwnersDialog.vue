<!-- TODO: Fix card to put buttons at the bottom -->
<!-- TODO: Make only the v-list scroll, keep height of everything else -->
<!-- TODO: Find way to clear v-autocomplete once selected-->
<template>
  <v-card height="500px">
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
          :disabled="editDisabled"
          :search-input.sync="search"
          hide-no-data
          clearable
          auto-select-first
          item-text="name"
          placeholder="Search by name or username"
          solo
          outlined
          flat
          return-object
        />
      </v-row>
      <v-divider />
      <v-row class="mx-1">
        <v-list
          width="100%"
          height="100%"
          class="px-6"
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
      class="mx-1"
    >
      <v-btn
        tile
        text
        @click="cancel"
      >
        Cancel
      </v-btn>
      <v-btn
        tile
        text
        color="primary"
        :disabled="editDisabled"
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
// import _ from 'lodash';
// const listToObject = (list) => (list.reduce((acc, owner) => ({ [owner.id]: owner, ...acc }), {}));


const userFormatConversion = (users) => users.map(({
  _id, _accessLevel, login, firstName, lastName,
}) => ({
  id: _id, level: _accessLevel, login, name: `${firstName} ${lastName}`,
}));


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
      newOwners: [...this.owners],
      items: [],
    };
  },
  computed: {
    user,
    editDisabled() {
      if (!this.user) return true;
      return !this.owners.find((owner) => owner.id === this.user._id);
    },
    ...mapState('girder', ['currentDandiset']),
  },
  watch: {
    async search(val, oldVal) {
      if (!this.search || this.loadingUsers || val === oldVal) return;

      this.loadingUsers = true;
      const { data } = await girderRest.get('/user/', { params: { text: this.search } });

      // Needed to match existing owner document schema
      this.items = userFormatConversion(data);

      this.loadingUsers = false;
    },
    selection(val) {
      if (!val || this.newOwners.find((x) => x.id === val.id)) return;

      this.newOwners.push(val);
      this.search = null;
      this.selection = null;
    },
  },
  methods: {
    removeOwner(index) {
      this.newOwners.splice(index, 1);
    },
    cancel() {
      this.$emit('close');
    },
    async save() {
      const { identifier } = this.currentDandiset.meta.dandiset;
      const formattedOwners = this.newOwners.map((owner) => ({ _id: owner.id }));

      const { data } = await girderRest.put(`/dandi/${identifier}/owners`, formattedOwners);
      this.setCurrentDandisetOwners(data);
      this.cancel();
    },
    ...mapMutations('girder', ['setCurrentDandisetOwners']),
  },
};
</script>
