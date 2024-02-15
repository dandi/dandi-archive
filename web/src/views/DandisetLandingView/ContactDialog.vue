<template>
  <v-menu
    offset-y
    left
  >
    <template
      #activator="{ on, attrs }"
    >
      <v-btn
        id="download"
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
        Select an e-mail Recipient
      </v-card-title>
      <v-list>
        <v-tooltip
          :disabled="loggedIn() || !owners"
          open-on-hover
          right
        >
          <template #activator="{ on }">
            <v-list-item
              v-on="on"
              :class="(loggedIn() || !owners) ? 'black--text' : 'grey--text'"
              :selectable="!loggedIn()"
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
          </template>
          <span v-if="!loggedIn()"> You must me logged in to contact the owner </span>
          <span v-else> No owner e-mail available </span>
        </v-tooltip>
      <v-divider />
        <v-tooltip
            :disabled="contacts"
            open-on-hover
            right
          >

          <template #activator="{ on }">
          <v-list-item
            v-on="on"
            :class=" !owners ? 'black--text' : 'grey--text'"
            :selectable="!owners"
            :href="makeTemplate(contacts)"
          >
          <v-icon
            color="primary"
            left
            small
          >
            mdi-card-account-mail
          </v-icon>
            Contact Person
          </v-list-item>
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

const store = useDandisetStore();
const owners = computed(() => store.owners?.map((owner) => owner.username).toString());
const contacts = computed(() => store.dandiset?.metadata?.contributor?.map((contact) => contact.roleName?.includes("dcite:ContactPerson") ? contact.email: '').toString());
const currentDandiset = computed(() => store.dandiset);

const makeTemplate = (contact: string | undefined) => {
  if (!contact) {
    return '';
  }
  // Subject is: Regarding [dandiset_name]  [dandiset_id]
  return `mailto:${contact}?subject=Regarding%20Dandiset%20${currentDandiset?.value?.name}%20${currentDandiset?.value?.metadata?.id}`;
};


</script>
<style scoped>
.v-btn--outlined {
  border: thin solid #E0E0E0;
  color: #424242;
  font-weight: 400;
}
</style>
