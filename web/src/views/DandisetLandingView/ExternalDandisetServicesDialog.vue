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
        </v-tooltip>
        <v-tooltip
          open-on-hover
          location="left"
        >
          <template #activator="{ props }">
            <div v-bind="props">
              <v-list-item
                :href="aiEditorURL"
                target="_blank"
                rel="noopener"
              >
                <v-icon
                  color="primary"
                  start
                  size="small"
                >
                  mdi-robot
                </v-icon>
                AI Metadata Editor (Beta)
              </v-list-item>
            </div>
          </template>
          <span>Open the Dandiset in the AI assisted metadata editor (Beta)</span>
        </v-tooltip>
        <v-tooltip
          v-if="atlas"
          open-on-hover
          location="left"
        >
          <template #activator="{ props }">
            <div v-bind="props">
              <v-list-item
                :href="atlasURL"
                target="_blank"
                rel="noopener"
              >
                <v-icon
                  color="primary"
                  start
                  size="small"
                >
                  mdi-brain
                </v-icon>
                DANDI Atlas
              </v-list-item>
            </div>
          </template>
          <span>Browse the Dandiset by brain region in {{ atlas.name }}</span>
        </v-tooltip>
      </v-list>
    </v-card>
  </v-menu>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useDandisetStore } from '@/stores/dandiset';
import { useInstanceStore } from '@/stores/instance';
import type { Atlas } from '@/utils/atlas';
import { atlasDandisetURL, getAtlasForDandiset } from '@/utils/atlas';

const store = useDandisetStore();
const instanceStore = useInstanceStore();
instanceStore.load();

const currentDandiset = computed(() => store.dandiset);

const neurosiftURL = computed(() => {
  if (!currentDandiset.value) {
    throw new Error('Dandiset is undefined');
  }

  if (!currentDandiset.value.metadata) {
    throw new Error('Dandiset metadata is undefined');
  }

  const metadata = currentDandiset.value.metadata;
  const dandisetId = currentDandiset.value.dandiset.identifier;
  const dandisetVersion = metadata.version;
  const stagingParam = instanceStore.isSandbox ? '&staging=1' : '';

  return `https://neurosift.app/dandiset/${dandisetId}?dandisetVersion=${dandisetVersion}${stagingParam}`;
});

const aiEditorURL = computed(() => {
  if (!currentDandiset.value) {
    throw new Error('Dandiset is undefined');
  }

  const dandisetId = currentDandiset.value.dandiset.identifier;
  const baseApiUrl = import.meta.env.VITE_APP_DANDI_API_ROOT;
  return `https://medit.dandiarchive.org/?dandiset=${dandisetId}&instance=${baseApiUrl}`;
});

// The atlas viewer only indexes Dandisets on the production instance, so identifiers
// from any other deployment would resolve to unrelated data.
const isProductionDandiset = computed(
  () => !!currentDandiset.value?.metadata?.url?.startsWith('https://dandiarchive.org/'),
);

const atlas = ref<Atlas | undefined>();

watch([currentDandiset, isProductionDandiset], async () => {
  atlas.value = undefined;
  if (!isProductionDandiset.value) {
    return;
  }

  const dandisetId = currentDandiset.value!.dandiset.identifier;
  const result = await getAtlasForDandiset(dandisetId);

  // Discard the result if the user navigated to another Dandiset while it was in flight.
  if (currentDandiset.value?.dandiset.identifier === dandisetId) {
    atlas.value = result;
  }
}, { immediate: true });

const atlasURL = computed(
  () => (atlas.value
    ? atlasDandisetURL(atlas.value.key, currentDandiset.value!.dandiset.identifier)
    : undefined),
);

</script>
