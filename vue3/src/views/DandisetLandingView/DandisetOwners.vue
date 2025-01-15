<template>
  <v-card
    outlined
    class="mt-4 px-3 pb-5"
  >
    <v-row
      no-gutters
      class="my-1"
    >
      <v-row
        no-gutters
        class="my-1 ml-1"
      >
        <div class="black--text text-h5">
          Owners
        </div>
      </v-row>
    </v-row>

    <v-row class="my-1">
      <v-col cols="12">
        <v-chip
          v-for="(owner, i) in limitedOwners"
          :key="i"
          color="grey lighten-4"
          text-color="grey darken-2"
          class="font-weight-medium ma-1"
          style="border: 1px solid #E0E0E0 !important;"
        >
          {{ owner.name || owner.username }}
        </v-chip>
        <span
          v-if="numExtraOwners"
          class="ml-1 text--secondary"
        >
          +{{ numExtraOwners }} more...
        </span>
      </v-col>
    </v-row>

    <v-row
      class="justify-center"
      no-gutters
    >
      <v-dialog
        v-model="ownerDialog"
        width="80%"
        persistent
      >
        <template #activator="{ on }">
          <v-tooltip
            :disabled="!manageOwnersDisabled"
            left
          >
            <template #activator="{ on: tooltipOn }">
              <div
                style="width: 100%;"
                v-on="tooltipOn"
              >
                <v-btn
                  id="manage"
                  depressed
                  :disabled="manageOwnersDisabled"
                  color="light-blue lighten-5"
                  class="light-blue--text text--lighten-1 justify-start"
                  block
                  v-on="on"
                >
                  <v-icon
                    class="pr-2"
                  >
                    mdi-account-plus
                  </v-icon>
                  Manage Owners
                </v-btn>
              </div>
            </template>
            <template v-if="loggedIn()">
              You must be an owner to manage ownership.
            </template>
            <template v-else>
              You must be logged in to manage ownership.
            </template>
          </v-tooltip>
        </template>
        <DandisetOwnersDialog
          v-if="owners"
          :owners="owners"
          @close="ownerDialog = false"
        />
      </v-dialog>
    </v-row>
  </v-card>
</template>

<script setup lang="ts">
import { loggedIn, user } from '@/rest';
import { useDandisetStore } from '@/stores/dandiset';
import DandisetOwnersDialog from '@/components/DLP/DandisetOwnersDialog.vue';
import { computed, ref } from 'vue';

const store = useDandisetStore();

const ownerDialog = ref(false);
const owners = computed(() => store.owners);

const manageOwnersDisabled = computed(() => {
  if (user.value?.admin) {
    return false;
  }
  if (!user.value || !owners.value) {
    return true;
  }
  return !owners.value.find((owner) => owner.username === user.value?.username);
});
const limitedOwners = computed(() => {
  if (!owners.value) {
    return [];
  }
  return owners.value.slice(0, 5);
});
const numExtraOwners = computed(() => {
  if (!owners.value) {
    return 0;
  }
  return owners.value.length - limitedOwners.value.length;
});
</script>
