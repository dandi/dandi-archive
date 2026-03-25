<template>
  <v-card class="rounded-0 elevation-0 pb-2">
    <v-card-title>
      Owners
    </v-card-title>

    <v-card-text class="pb-2">
      <v-chip
        v-for="(owner, i) in limitedOwners"
        :key="i"
        color="grey-lighten-4"
        class="font-weight-medium ma-1 text-grey-darken-2"
        style="border: 1px solid #E0E0E0 !important;"
      >
        {{ owner.name || owner.username }}
      </v-chip>
      <v-btn
        v-if="numExtraOwners"
        variant="text"
        color="secondary"
        size="small"
        class="ml-1 text-none"
        @click="showAllOwnersDialog = true"
      >
        +{{ numExtraOwners }} more...
      </v-btn>

      <!-- Dialog to show all owners -->
      <v-dialog
        v-model="showAllOwnersDialog"
        width="unset"
        max-width="1000"
      >
        <v-card>
          <v-card-title class="text-h5 d-flex align-center">
            <v-icon
              size="large"
              class="mr-2"
            >
              mdi-account-group
            </v-icon>
            All {{ owners?.length || 0 }} Owners
          </v-card-title>
          <v-divider />
          <v-card-text class="pt-4">
            <v-row>
              <v-col
                v-for="(ownersChunk, chunkIndex) in chunk(owners, 10)"
                :key="chunkIndex"
                cols="auto"
              >
                <v-list>
                  <v-list-item
                    v-for="(owner, i) in ownersChunk"
                    :key="i"
                    class="mb-2"
                  >
                    <template #prepend>
                      <v-avatar
                        color="primary"
                        class="mr-3"
                      >
                        <v-icon color="white">
                          mdi-account
                        </v-icon>
                      </v-avatar>
                    </template>
                    <v-list-item-title class="font-weight-medium">
                      {{ owner.name || owner.username }}
                    </v-list-item-title>
                    <v-list-item-subtitle v-if="owner.name">
                      {{ owner.username }}
                    </v-list-item-subtitle>
                  </v-list-item>
                </v-list>
              </v-col>
            </v-row>
          </v-card-text>
          <v-divider />
          <v-card-actions>
            <v-spacer />
            <v-btn
              color="primary"
              variant="text"
              @click="showAllOwnersDialog = false"
            >
              Close
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </v-card-text>

    <!-- Manage Owners dialog -->
    <v-card-actions
      class="justify-center px-4"
      no-gutters
    >
      <v-dialog
        v-model="ownerDialog"
        width="80%"
        persistent
      >
        <template #activator="{ props: dialogProps }">
          <v-tooltip
            :disabled="!manageOwnersDisabled"
            location="left"
          >
            <template #activator="{ props: tooltipProps }">
              <div
                style="width: 100%;"
                v-bind="tooltipProps"
              >
                <v-btn
                  id="manage"
                  variant="tonal"
                  :disabled="manageOwnersDisabled"
                  color="primary"
                  class="justify-start"
                  block
                  prepend-icon="mdi-account-plus"
                  v-bind="dialogProps"
                >
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
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { chunk } from 'lodash';
import { loggedIn, user } from '@/rest';
import { useDandisetStore } from '@/stores/dandiset';
import DandisetOwnersDialog from '@/components/DLP/DandisetOwnersDialog.vue';
import { computed, ref } from 'vue';

const store = useDandisetStore();

const ownerDialog = ref(false);
const showAllOwnersDialog = ref(false);
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
