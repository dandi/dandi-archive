<template>
  <v-menu
    offset-y
    left
  >
    <template
      #activator="{ on, attrs }"
    >
      <v-btn
        id="external-dandiset-services"
        outlined
        block
        v-bind="attrs"
        v-on="on"
      >
        <v-icon
          color="primary"
          left
        >
          mdi-web
        </v-icon>
        <span>External services</span>
        <v-spacer />
        <v-icon right>
          mdi-chevron-down
        </v-icon>
      </v-btn>
    </template>
    <v-card
    >
      <v-card-title class="pb-0" style="min-width: fit-content;">
        Select an external service:
      </v-card-title>
      <v-list>
        <v-tooltip
          open-on-hover
          left
        >
          <template #activator="{ on }">
            <div
            v-on="on"
            >
              <v-list-item
                :href="openInNeurosift()"
              >
                <v-icon
                  color="primary"
                  left
                  small
                >
                  mdi-web
                </v-icon>
                Neurosift
              </v-list-item>
            </div>
          </template>
          <span>Open the Dandiset in Neurosift</span>
        </v-tooltip>
      </v-list>
    </v-card>
  </v-menu>
</template>
<script setup lang="ts">
import { computed } from 'vue';
import { useDandisetStore } from '@/stores/dandiset';

const store = useDandisetStore();

const currentDandiset = computed(() => store.dandiset);

const openInNeurosift = () => {
  const fullId = currentDandiset.value?.metadata?.id;
  // e.g., DANDI:000776/0.241009.1509
  if (!fullId) {
    alert('Unexpected: No id field found in the metadata');
    return;
  }
  const dandisetId = fullId.split('/')[0].split(':')[1];
  const dandisetVersion = fullId.split('/')[1];
  if (!dandisetId || !dandisetVersion) {
    alert(`Unexpected: Invalid id field found in the metadata: ${fullId}`);
    return;
  }
  return `https://neurosift.app/?p=/dandiset&dandisetId=${dandisetId}&dandisetVersion=${dandisetVersion}`;
};

</script>
<style scoped>
.v-btn--outlined {
  border: thin solid #E0E0E0;
  color: #424242;
  font-weight: 400;
}
</style>
