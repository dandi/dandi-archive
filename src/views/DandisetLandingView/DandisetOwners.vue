<template>
  <v-card
    v-if="currentDandiset"
    height="100%"
    class="px-3 py-1"
    outlined
  >
    <v-row
      no-gutters
      class="my-1 ml-1"
    >
      <div class="black--text text-h5">
        Ownership
      </div>
    </v-row>
    <v-row>
      <template v-if="!owners || !owners.length">
        <v-row
          align="center"
          class="mx-1 px-6"
        >
          No owners
        </v-row>
      </template>
      <template v-else>
        <v-tooltip
          v-if="showOwnerSearchBox"
          top
          :disabled="userCanModifyDandiset"
        >
          <template #activator="{ on }">
            <div v-on="on">
              <v-row class="mx-2 px-2">
                <v-autocomplete
                  v-model="selection"
                  :items="items"
                  :disabled="!userCanModifyDandiset"
                  :loading="loadingUsers"
                  :search-input.sync="search"
                  hide-no-data
                  clearable
                  auto-select-first
                  item-text="result"
                  placeholder="enter email address"
                  outlined
                  flat
                  return-object
                  @update:search-input="throttledUpdate"
                />
              </v-row>
            </div>
          </template>
          <template v-if="loggedIn">
            You must be an owner to manage ownership.
          </template>
          <template v-else>
            You must be logged in to manage ownership.
          </template>
        </v-tooltip>
        <v-row class="mx-2 px-2">
          <v-chip
            v-for="(owner, i) in newOwners"
            :key="i"
            color="light-blue lighten-4"
            text-color="light-blue darken-3"
            class="font-weight-medium ma-1"
            :close="userCanModifyDandiset"
            @click:close="removeOwner(i)"
          >
            {{ owner.name || owner.username }}
          </v-chip>
        </v-row>
      </template>
    </v-row>
  </v-card>
</template>

<script lang="ts">
import {
  defineComponent, reactive, ref, computed, Ref, ComputedRef, watch,
} from '@vue/composition-api';

import { debounce } from 'lodash';

import { draftVersion } from '@/utils/constants';
import { publishRest, loggedIn as loggedInFunc } from '@/rest';
import store from '@/store';
import { User } from '@/types';

interface UserResult extends User {
  result: string
}

// Includes a field `result` on each user which is the value displayed in the UI
const appendResult = (users: User[]): UserResult[] => users?.map((u: User) => ({ ...u, result: (u.name) ? `${u.name} (${u.username})` : u.username }));

export default defineComponent({
  name: 'DandisetOwners',
  props: {
    userCanModifyDandiset: {
      type: Boolean,
      required: true,
    },
  },
  setup() {
    const currentDandiset = computed(() => store.state.dandiset.publishDandiset);
    const owners = computed(() => store.state.dandiset.owners);

    const search = ref('');
    const loadingUsers = ref(false);
    const selection: Ref<UserResult|null> = ref(null);
    const items: Ref<User[]> = ref([]);

    const newOwners: UserResult[] = reactive([]);
    watch(() => owners.value, () => (
      owners.value ? Object.assign(newOwners, appendResult(owners.value)) : null),
    { immediate: true });

    const loggedIn: ComputedRef<boolean> = computed(loggedInFunc);

    const showOwnerSearchBox = computed(
      // Only show the search box to logged in users on DRAFT versions
      () => loggedIn.value && currentDandiset.value?.version === draftVersion,
    );

    function setOwners(ownersToSet: User[]) {
      store.commit.setOwners(ownersToSet);
    }

    const throttledUpdate = debounce((async () => {
      if (!search.value) return;

      loadingUsers.value = true;
      const users = await publishRest.searchUsers(search.value);
      items.value = appendResult(users);
      loadingUsers.value = false;
    }), 200);

    async function save() {
      if (currentDandiset.value?.dandiset) {
        const { identifier } = currentDandiset.value.dandiset;
        const { data } = await publishRest.setOwners(identifier, newOwners);
        setOwners(data);
      }
    }

    async function removeOwner(index: number) {
      newOwners.splice(index, 1);
      await save();
    }

    watch(selection, async () => {
      // Verify that the selected user hasn't already been selected
      if (selection.value && !newOwners.find((x) => x.username === selection.value?.username)) {
        newOwners.push(selection.value);
      }
      // Clear the search field, if it isn't already
      if (selection.value) {
        selection.value = null;
      }

      await save();
    });

    return {
      currentDandiset,
      owners,
      selection,
      items,
      loadingUsers,
      search,
      throttledUpdate,
      loggedIn,
      newOwners,
      removeOwner,
      draftVersion,
      showOwnerSearchBox,
    };
  },
});
</script>
