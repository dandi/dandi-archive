<template>
  <v-menu location="left">
    <template #activator="{ props }">
      <v-btn
        id="contact"
        variant="outlined"
        block

        v-bind="props"
      >
        <v-icon
          color="primary"
          start
        >
          mdi-card-account-mail
        </v-icon>
        <span>Contact</span>
        <v-spacer />
        <v-icon end>
          mdi-chevron-down
        </v-icon>
      </v-btn>
    </template>
    <v-card>
      <v-card-title
        class="pb-0"
        style="min-width: fit-content;"
      >
        Select an e-mail recipient:
      </v-card-title>
      <v-list>
        <v-tooltip
          :disabled="!disableDandisetOwnersButton"
          open-on-hover
          location="left"
        >
          <template #activator="{ props }">
            <div
              v-bind="props"
            >
              <v-list-item
                :disabled="disableDandisetOwnersButton"
                :href="makeTemplate(dandisetOwnerEmails)"
              >
                <v-icon
                  color="primary"
                  start
                  size="small"
                >
                  mdi-card-account-mail
                </v-icon>
                Dandiset Owners
              </v-list-item>
            </div>
          </template>
          <span v-if="!loggedIn()"> You must be logged in to contact the owner </span>
          <span v-if="!dandisetOwnerEmails?.length"> No owner e-mail available </span>
        </v-tooltip>
        <v-divider />
        <v-tooltip
          :disabled="!disableContactPersonButton"
          open-on-hover
          location="left"
        >
          <template #activator="{ props }">
            <div v-bind="props">
              <v-list-item
                :disabled="disableContactPersonButton"
                :href="makeTemplate(dandisetContactPersonEmails)"
              >
                <v-icon
                  color="primary"
                  start
                  size="small"
                >
                  mdi-card-account-mail
                </v-icon>
                Dandiset Contact Person
              </v-list-item>
            </div>
          </template>
          <span> No contact e-mail available </span>
        </v-tooltip>
      </v-list>
    </v-card>
  </v-menu>
</template>
<script setup lang="ts">
import { computed } from 'vue';
import { useDandisetStore } from '@/stores/dandiset';
import { loggedIn } from '@/rest';
import type { User, Person, Organization, Email} from '@/types';

const store = useDandisetStore();

const currentDandiset = computed(() => store.dandiset);

const dandisetOwnerEmails = computed(() => store.owners?.map((owner: User) => owner.email) || []);

const dandisetContactPersonEmails = computed(() =>
  currentDandiset.value?.metadata?.contributor?.filter(
    (contact: Person | Organization) =>
      contact.roleName?.includes("dcite:ContactPerson")
    )
    .map((contact: Person | Organization) =>
      contact.email as Email
    )
    // Exclude users missing an email
    .filter((email?: Email) => email !== undefined)
    // Exclude users with an empty email
    .filter((email: Email) => email !== '')
    || []
);

const makeTemplate = (contacts: string[]) => {
  if (currentDandiset.value === undefined) {
    throw new Error('Dandiset is undefined.');
  }
  if (currentDandiset.value){
    const subject = encodeURIComponent(`Regarding Dandiset ${currentDandiset.value.dandiset.identifier} ("${currentDandiset.value.name}")`);
    const contact = contacts.join(',');
    return `mailto:${contact}?subject=${subject}`;
  }
};

const disableContactPersonButton = computed(() => !dandisetContactPersonEmails.value?.length)
const disableDandisetOwnersButton = computed(
  // Only logged in users can access owners' emails
  () => !loggedIn() || !dandisetOwnerEmails.value?.length
);

</script>
<style scoped>
.v-btn--outlined {
  border: thin solid #E0E0E0;
  color: #424242;
  font-weight: 400;
}
</style>
