<template>
  <v-menu>
    <template #activator="{ props }">
      <v-list-item
        id="external-dandiset-services"
        class="justify-space-between border rounded-b"
        v-bind="props"
      >
        <template #prepend>
          <v-icon
            color="primary"
            start
          >
            mdi-web
          </v-icon>
          <v-list-item-title>Open with</v-list-item-title>
        </template>
        <template #append>
          <v-icon end>
            mdi-chevron-down
          </v-icon>
        </template>
      </v-list-item>
    </template>
    <v-card>
      <v-list>
        <v-tooltip
          open-on-hover
          location="left"
        >
          <template #activator="{ props }">
            <div v-bind="props">
              <v-list-item
                :href="neurosiftURL"
                target="_blank"
              >
                <v-icon
                  color="primary"
                  start
                  size="small"
                >
                  mdi-web
                </v-icon>
                Neurosift
              </v-list-item>
            </div>
          </template>
          <span>Open the Dandiset in Neurosift</span>
          <template #activator="{ props }">
            <div v-bind="props">
              <v-list-item
                :href="brainlifeURL"
                target="_blank"
              >
                <v-icon
                  color="primary"
                  start
                  size="small"
                >
                  mdi-web
                </v-icon>
                Brainlife
              </v-list-item>
            </div>
          </template>
          <span>Open the Dandiset in Brainlife</span>
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

const neurosiftURL = computed(() => {
  if (!currentDandiset.value) {
    throw new Error('Dandiset is undefined');
  }

  if (!currentDandiset.value.metadata) {
    throw new Error('Dandiset metadata is undefined');
  }

  if (!currentDandiset.value.metadata.url) {
    throw new Error('Dandiset metadata.url is undefined');
  }

  const metadata = currentDandiset.value.metadata;
  const dandisetId = currentDandiset.value.dandiset.identifier;
  const dandisetVersion = metadata.version;
  const stagingParam = metadata.url!.startsWith('https://sandbox.dandiarchive.org/') ? '&staging=1' : '';

  return `https://neurosift.app/dandiset/${dandisetId}?dandisetVersion=${dandisetVersion}${stagingParam}`;
});

const brainlifeURL = computed(() => {
  if (!currentDandiset.value) {
    throw new Error('Dandiset is undefined');
  }

  if (!currentDandiset.value.metadata) {
    throw new Error('Dandiset metadata is undefined');
  }

  if (!currentDandiset.value.metadata.url) {
    throw new Error('Dandiset metadata.url is undefined');
  }

  const metadata = currentDandiset.value.metadata;
  const dandisetId = currentDandiset.value.dandiset.identifier;
  const dandisetVersion = metadata.version;
  const stagingParam = metadata.url!.startsWith('https://sandbox.dandiarchive.org/') ? 'dandi-staging/' : '';

  return `https://brainlife.io/dandiarchive/${stagingParam}${dandisetId}/${dandisetVersion}`;
});

</script>
