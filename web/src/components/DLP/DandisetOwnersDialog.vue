<template>
  <v-card
    class="flex-grow-0"
    :max-height="$vuetify.breakpoint.xs ? undefined : '90vh'"
    :height="$vuetify.breakpoint.xs ? '100%' : undefined"
  >
    <v-card-title class="justify-space-between">
      <span class="font-weight-light">Manage Owners</span>
      <v-btn
        :small="$vuetify.breakpoint.xs"
        color="info"
        elevation="0"
        @click="save() && $emit('close')"
      >
        Done
      </v-btn>
    </v-card-title>

    <v-divider />

    <v-row no-gutters>
      <v-col
        :cols="$vuetify.breakpoint.xs ? 12 : 6"
        class="d-flex flex-column"
      >
        <div class="mx-3 mt-4 mb-2">
          <v-text-field
            v-model="searchQuery"
            dense
            label="Filter users (by name/email)"
            hide-details="auto"
            outlined
            @keyup="throttledUpdate"
          />
        </div>
        <div class="flex-grow-1">
          <div
            v-for="(result, i) in searchResults"
            :key="i"
          >
            <v-divider class="mx-0" />
            <div
              class="mx-3 px-2"
              style="width: 100%"
            >
              <div class="d-flex justify-space-between">
                <v-row class="align-center">
                  <v-checkbox
                    color="info"
                    :input-value="isSelected(result)"
                    @click="checkBoxHandler(result)"
                  />
                  <span class="text-body-2 font-weight-medium grey--text text--darken-3">
                    {{ result.name || result.username }}
                  </span>
                  <span
                    v-if="result.name"
                    class="text-caption ml-1 pt-1"
                  >
                    {{ result.username }}
                  </span>
                </v-row>
                <v-btn
                  x-small
                  height="2rem"
                  color="info"
                  elevation="0"
                  class="mr-4 my-auto"
                  @click="addOwner(result)"
                >
                  <v-icon>
                    mdi-arrow-right
                  </v-icon>
                </v-btn>
              </div>
            </div>
          </div>
        </div>
        <v-card-actions class="elevation-10 mt-1 px-3 justify-space-between">
          <v-btn
            class="pa-2"
            text
            @click="clearForm"
          >
            Clear form
          </v-btn>
          <v-btn
            class="pa-2 py-5 grey darken-3 white--text"
            depressed
            @click="addSelected"
          >
            <span class="mr-6 ml-2">
              Add selected
            </span>
            <v-icon>
              mdi-arrow-right
            </v-icon>
          </v-btn>
        </v-card-actions>
      </v-col>
      <v-col class="grey lighten-3">
        <div class="my-6">
          <v-card
            v-for="(owner, i) in newOwners"
            :key="i"
            class="mx-5 pa-3"
            outlined
          >
            <div class="d-flex flex-wrap justify-space-between">
              <span class="text-body-2">
                <v-icon class="mr-2">mdi-account</v-icon>
                <span class="text-body-2">
                  {{
                    `
                    ${owner.name || owner.username}
                    ${owner.username === user.username ? ' (you)' : ''}
                    `
                  }}
                </span>
              </span>

              <span>
                <v-btn
                  v-if="newOwners.length > 1"
                  text
                  small
                  @click="removeOwner(owner)"
                >
                  <v-icon
                    color="error"
                    left
                  >mdi-minus-circle
                  </v-icon>
                  <span class="font-weight-medium">
                    Remove
                  </span>
                </v-btn>
              </span>
            </div>
          </v-card>
        </div>
      </v-col>
    </v-row>
    <v-dialog
      v-model="adminWarningDisplay"
      max-width="60vw"
      persistent
    >
      <v-card class="pb-3">
        <v-card-title class="text-h5 font-weight-light">
          WARNING
        </v-card-title>
        <v-divider class="my-3" />
        <v-card-text>
          This action will modify the owners of this dandiset. You are not an owner of this
          dandiset, but as an admin you may still perform this action.
        </v-card-text>
        <v-card-text>
          Would you like to proceed?
        </v-card-text>

        <v-card-actions>
          <v-btn
            color="error"
            depressed
            @click="save"
          >
            Yes
          </v-btn>
          <v-btn
            depressed
            @click="adminWarningDisplay = false"
          >
            No
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script lang="ts">
import { debounce } from 'lodash';

import { dandiRest } from '@/rest';
import store from '@/store';
import {
  computed, defineComponent, Ref, ref, watch,
} from '@vue/composition-api';
import { User } from '@/types';

export default defineComponent({
  name: 'DandisetOwnersDialog',
  props: {
    owners: {
      type: Array,
      required: true,
    },
  },
  setup() {
    const currentDandiset = computed(() => store.state.dandiset.dandiset);
    const owners = computed(() => store.state.dandiset.owners);

    const searchQuery = ref('');
    const newOwners: Ref<User[]> = ref([]);

    // users with checkbox checked
    const selectedUsers: Ref<User[]> = ref([]);

    const adminWarningDisplay = ref(false);

    // eslint-disable-next-line no-underscore-dangle
    const _searchResults: Ref<User[]> = ref([]);
    const searchResults = computed(() => {
      const newOwnersUsernames = new Set(newOwners.value.map((u: User) => u.username));
      // only show non-owners in search results
      return _searchResults.value.filter((u: User) => !newOwnersUsernames.has(u.username));
    });

    // Clear search results if search field is empty
    watch(() => searchQuery.value, () => {
      if (!searchQuery.value) {
        _searchResults.value = [];
      }
    });

    const throttledUpdate = debounce(async () => {
      const users = await dandiRest.searchUsers(searchQuery.value);
      _searchResults.value = users;
    }, 200);

    watch(() => owners.value, () => (
      owners.value ? Object.assign(newOwners.value, owners.value) : null
    ),
    { immediate: true });

    const isSelected = (user: User) => selectedUsers.value.map(
      (u) => u.username,
    ).includes(user.username);
    const setOwners = (ownersToSet: User[]) => store.commit.dandiset.setOwners(ownersToSet);

    /**
     * Add a user as an owner
     */
    function addOwner(newOwner: User) {
      if (!newOwners.value.map((u: User) => u.username).includes(newOwner.username)) {
        newOwners.value.push(newOwner);
      }
    }

    function removeOwner(owner: User) {
      newOwners.value.splice(newOwners.value.map(
        (u: User) => u.username,
      ).indexOf(owner.username), 1);
    }

    function checkBoxHandler(user: User) {
      const selectedUsersUsernames = selectedUsers.value.map((u: User) => u.username);
      if (selectedUsersUsernames.includes(user.username)) {
        selectedUsers.value = selectedUsers.value.splice(
          selectedUsersUsernames.indexOf(user.username), 1,
        );
      } else {
        selectedUsers.value.push(user);
      }
    }

    function addSelected() {
      newOwners.value = newOwners.value.concat(selectedUsers.value);
      selectedUsers.value = [];
    }

    function clearForm() {
      selectedUsers.value = [];
    }

    async function save() {
      if (currentDandiset.value?.dandiset) {
        const userNotOwner = !owners.value
          ?.map((u: User) => u.username)
          .includes(dandiRest.user!.username);

        // If necessary, open display and return. Otherwise, proceed to save.
        if (!adminWarningDisplay.value && dandiRest.user?.admin && userNotOwner) {
          adminWarningDisplay.value = true;
          return;
        }

        const { identifier } = currentDandiset.value.dandiset;
        const { data } = await dandiRest.setOwners(identifier, newOwners.value);
        setOwners(data);
        adminWarningDisplay.value = false;
      }
    }

    const user = computed(() => dandiRest.user);

    return {
      searchQuery,
      searchResults,
      newOwners,
      throttledUpdate,
      addOwner,
      removeOwner,
      isSelected,
      save,
      clearForm,
      addSelected,
      checkBoxHandler,
      selectedUsers,
      user,
      adminWarningDisplay,
    };
  },
});
</script>
