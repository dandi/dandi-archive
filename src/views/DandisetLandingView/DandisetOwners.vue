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
          :key="owner.name || owner.username"
          color="grey lighten-4"
          text-color="grey darken-2"
          class="font-weight-medium ma-1"
          style="border: 1px solid #E0E0E0 !important;"
          close-icon="mdi-star-circle"
          :close="i === 0"
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
        width="50%"
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
            <template v-if="loggedIn">
              You must be an owner to manage ownership.
            </template>
            <template v-else>
              You must be logged in to manage ownership.
            </template>
          </v-tooltip>
        </template>
        <DandisetOwnersDialog
          :key="ownerDialogKey"
          :owners="owners"
          @close="ownerDialog = false"
        />
      </v-dialog>
    </v-row>
  </v-card>
</template>

<script>
import { mapState } from 'vuex';
import { loggedIn, user } from '@/rest';
import DandisetOwnersDialog from '@/components/DLP/DandisetOwnersDialog.vue';

export default {
  name: 'DandisetOwners',
  components: {
    DandisetOwnersDialog,
  },
  data() {
    return {
      labelClasses: 'mx-2 text--secondary',
      itemClasses: 'font-weight-medium',
      ownerDialog: false,
      ownerDialogKey: 0,
    };
  },
  computed: {
    user,
    loggedIn,
    currentDandiset() {
      return this.currentDandiset;
    },
    manageOwnersDisabled() {
      if (!this.loggedIn || !this.owners) return true;
      return !this.owners.find((owner) => owner.username === this.user.username);
    },
    limitedOwners() {
      if (!this.owners) return [];
      return this.owners.slice(0, 5);
    },
    numExtraOwners() {
      if (!this.owners) return 0;
      return this.owners.length - this.limitedOwners.length;
    },
    ...mapState('dandiset', {
      currentDandiset: (state) => state.dandiset,
      owners: (state) => state.owners,
    }),
  },
  watch: {
    ownerDialog() {
      // This is incremented to force re-render of the owner dialog
      this.ownerDialogKey += 1;
    },
  },
};
</script>
