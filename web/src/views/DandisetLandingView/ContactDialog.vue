<template>
  <v-menu
    offset-y
    left
  >
    <template
      #activator="{ on, attrs }"
    >
      <v-btn
        id="contact"
        outlined
        block
        v-bind="attrs"
        v-on="on"
      >
        <v-icon
          color="primary"
          left
        >
          mdi-card-account-mail
        </v-icon>
        <span>Contact</span>
        <v-spacer />
        <v-icon right>
          mdi-chevron-down
        </v-icon>
      </v-btn>
    </template>
    <v-card
    >
      <v-card-title class="pb-0" style="min-width: fit-content;">
        Select an e-mail recipient:
      </v-card-title>
      <v-list>
        <v-tooltip
          :disabled="!(loggedIn() || !isDisabled(owners))"
          open-on-hover
          left
        >
          <template #activator="{ on }">
            <div
            v-on="on"
            >
              <v-list-item
                :disabled="!loggedIn() || isDisabled(owners)"
                :href="makeTemplate(owners)"
              >
                <v-icon
                  color="primary"
                  left
                  small
                >
                  mdi-card-account-mail
                </v-icon>
                Dandiset Owners
              </v-list-item>
            </div>
          </template>
          <span v-if="!loggedIn()"> You must be logged in to contact the owner </span>
          <span v-if="isDisabled(owners)"> No owner e-mail available </span>
        </v-tooltip>
      <v-divider />
        <v-tooltip
            :disabled=!isDisabled(contacts)
            open-on-hover
            left
          >

          <template #activator="{ on }">
            <div v-on="on">
              <v-list-item
                :disabled="isDisabled(contacts)"
                :href="makeTemplate(contacts)"
              >
                <v-icon
                  color="primary"
                  left
                  small
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
const owners = computed(() => store.owners?.map((owner: User) => owner.email));
const contacts = computed(() =>
  store.dandiset?.metadata?.contributor?.filter(
    (contact: Person | Organization) =>
      contact.roleName?.includes("dcite:ContactPerson"))
    .map((contact: Person | Organization) =>
      contact.email as Email
    )
);
const currentDandiset = computed(() => store.dandiset);

const makeTemplate = (contacts: string[] | undefined) => {
  if (contacts === undefined) {
    throw new Error('Contact is undefined.');
  }
  if (currentDandiset.value === undefined) {
    throw new Error('Dandiset is undefined.');
  }
  if (currentDandiset.value){
    const subject = encodeURIComponent(`Regarding Dandiset ${currentDandiset.value.dandiset.identifier} ("${currentDandiset.value.name}")`);
    const contact = contacts.join(',');
    return `mailto:${contact}?subject=${subject}`;
  }
};

const isDisabled = (contacts: string[] | undefined): boolean =>
  contacts === undefined || contacts.length === 0 || contacts[0] === '';

</script>
<style scoped>
.v-btn--outlined {
  border: thin solid #E0E0E0;
  color: #424242;
  font-weight: 400;
}
</style>
