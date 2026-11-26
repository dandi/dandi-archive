<template>
  <section
    class="app-tiles"
    aria-labelledby="app-tiles-heading"
  >
    <h2
      id="app-tiles-heading"
      class="app-tiles-heading"
    >
      More ways to explore DANDI data
    </h2>
    <v-row dense>
      <v-col
        v-for="app in APPS"
        :key="app.name"
        cols="12"
        md="4"
      >
        <v-card
          :href="app.url"
          target="_blank"
          rel="noopener"
          class="app-tile d-flex align-center h-100 pa-3 ga-3"
        >
          <img
            :src="app.image"
            alt=""
            class="app-tile-image flex-shrink-0"
            width="144"
            height="81"
          >
          <div style="min-width: 0;">
            <div class="app-tile-name d-flex align-center">
              {{ app.name }}
              <v-icon
                size="x-small"
                class="ml-1 text-medium-emphasis"
              >
                mdi-open-in-new
              </v-icon>
            </div>
            <div class="text-body-2 text-medium-emphasis">
              {{ app.description }}
            </div>
          </div>
        </v-card>
      </v-col>
    </v-row>
  </section>
</template>

<script setup lang="ts">
import atlasImage from '@/assets/apps/atlas.jpg';
import notebooksImage from '@/assets/apps/notebooks.jpg';
import neurosiftImage from '@/assets/apps/neurosift.jpg';

// Apps built around DANDI that are hard to find from the archive itself.
const APPS = [
  {
    name: 'DANDI Atlas',
    description: 'Browse Dandisets by the brain regions they record from, on a 3D brain.',
    url: 'https://atlas.dandiarchive.org',
    image: atlasImage,
  },
  {
    name: 'DANDI Notebooks',
    description: 'Example notebooks for analyzing Dandisets, ready to run in Colab.',
    url: 'https://notebooks.dandiarchive.org',
    image: notebooksImage,
  },
  {
    name: 'Neurosift',
    description: 'Look inside and plot NWB files in your browser, without downloading them.',
    url: 'https://neurosift.app',
    image: neurosiftImage,
  },
];
</script>

<style scoped>
.app-tiles {
  margin-top: 28px;
}
.app-tiles-heading {
  font-size: 0.8125rem;
  font-weight: 500;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.75);
  margin-bottom: 10px;
}
.app-tile {
  text-decoration: none;
}
.app-tile-image {
  border-radius: 4px;
  object-fit: cover;
  border: 1px solid rgba(0, 0, 0, 0.08);
}
/* Below 600px a smaller preview leaves the text room. */
@media (max-width: 599px) {
  .app-tile-image {
    width: 96px;
    height: 54px;
  }
}
.app-tile-name {
  font-size: 1rem;
  font-weight: 500;
  line-height: 1.4;
}
</style>
