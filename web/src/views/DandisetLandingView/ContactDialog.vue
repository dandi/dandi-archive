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
        <v-list-item
          :href="`mailto:${owners}?subject=Regarding%20Dandiset%20${currentDandiset?.name}%20${currentDandiset?.metadata?.id} &body=${currentUser?.value?.username}`"
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
      <v-divider />

        <v-list-item
          :href="`mailto:${contacts}?subject=Regarding%20Dandiset%20${currentDandiset?.name}%20${currentDandiset?.metadata?.id} &body=${currentUser?.value?.username}`"
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

      </v-list>
    </v-card>
  </v-menu>
</template>
<script setup lang="ts">
import { computed } from 'vue';
import { useDandisetStore } from '@/stores/dandiset';
import { user } from '@/rest';

const store = useDandisetStore();
const owners = computed(() => store.owners?.map((owner) => owner.username).toString());
const contacts = computed(() => store.dandiset?.metadata?.contributor?.map((contact) => contact.roleName?.includes("dcite:ContactPerson") ? contact.email: '').toString());
const currentUser = computed(() => user);
const currentDandiset = computed(() => store.dandiset);
currentDandiset.value?.metadata?.id

</script>
<style scoped>
.v-btn--outlined {
  border: thin solid #E0E0E0;
  color: #424242;
  font-weight: 400;
}
</style>
