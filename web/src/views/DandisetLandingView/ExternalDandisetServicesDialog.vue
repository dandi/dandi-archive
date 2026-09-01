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
          v-for="service in services"
          :key="service.name"
          open-on-hover
          location="left"
        >
          <template #activator="{ props }">
            <div v-bind="props">
              <v-list-item
                :href="service.url"
                target="_blank"
                rel="noopener"
              >
                <v-icon
                  color="primary"
                  start
                  size="small"
                >
                  {{ service.icon }}
                </v-icon>
                {{ service.name }}
              </v-list-item>
            </div>
          </template>
          <span>{{ service.tooltip }}</span>
        </v-tooltip>
      </v-list>
    </v-card>
  </v-menu>
</template>
<script setup lang="ts">
import { useExternalDandisetServices } from '@/utils/externalDandisetServices';

const services = useExternalDandisetServices();
</script>
