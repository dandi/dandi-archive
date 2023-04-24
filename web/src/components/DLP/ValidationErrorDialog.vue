<template>
  <v-card
    min-height="90vh"
    class="pa-2"
  >
    <v-tabs v-model="tab">
      <v-tab
        v-if="showMetadataTab"
        key="metadata"
        href="#metadata"
      >
        Metadata
      </v-tab>
      <v-tab
        v-if="showAssetsTab"
        key="assets"
        href="#assets"
      >
        Assets
      </v-tab>
    </v-tabs>
    <v-tabs-items v-model="tab">
      <!-- Metadata -->
      <v-tab-item
        v-if="showMetadataTab"
        key="metadata"
        value="metadata"
        :transition="false"
      >
        <v-btn
          v-if="owner"
          class="mt-1"
          color="primary"
          @click="$emit('openMeditor')"
        >
          Fix issues
        </v-btn>
        <v-list
          class="overflow-y-auto"
        >
          <div
            v-for="(error, index) in versionValidationErrors"
            :key="index"
          >
            <v-list-item>
              <v-list-item-icon>
                <v-icon>
                  {{ getValidationErrorIcon(error.field) }}
                </v-icon>
              </v-list-item-icon>

              <v-list-item-content>
                <template v-if="error.field">
                  {{ error.field }}:
                </template>
                {{ error.message }}
              </v-list-item-content>
            </v-list-item>
            <v-divider />
          </div>
        </v-list>
      </v-tab-item>

      <!-- Assets -->
      <v-tab-item
        v-if="showAssetsTab"
        key="assets"
        value="assets"
        :transition="false"
      >
        <v-list
          class="overflow-y-auto"
        >
          <v-expansion-panels multiple>
            <v-expansion-panel
              v-for="(errors, path) in assetValidationErrors"
              :key="path"
            >
              <v-expansion-panel-header>
                {{ path }}
              </v-expansion-panel-header>
              <v-expansion-panel-content>
                <v-list-item
                  v-for="error in errors"
                  :key="`${error.field}-${error.message}`"
                >
                  <v-list-item-icon>
                    <v-icon>
                      {{ getValidationErrorIcon(error.field) }}
                    </v-icon>
                  </v-list-item-icon>
                  <v-list-item-content>
                    <template v-if="error.field">
                      {{ error.field }}:
                    </template>
                    {{ error.message }}
                  </v-list-item-content>
                </v-list-item>
              </v-expansion-panel-content>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-list>
      </v-tab-item>
    </v-tabs-items>
  </v-card>
</template>

<script setup lang="ts">
import type { ValidationError } from '@/types';
import type { PropType } from 'vue';
import { watch, computed, ref } from 'vue';

import { VALIDATION_ICONS } from '@/utils/constants';

const props = defineProps({
  assetValidationErrors: {
    type: Object as PropType<Record<string, ValidationError[]>>,
    required: true,
  },
  versionValidationErrors: {
    type: Array as PropType<ValidationError[]>,
    required: true,
  },
  selectedTab: {
    type: String as PropType<'metadata' | 'assets'>,
    required: false,
    default: 'metadata',
  },
  owner: {
    type: Boolean,
    required: false,
    default: false,
  },
});

const tab = ref(props.selectedTab);
watch(() => props.selectedTab, (val) => {
  tab.value = val;
});

const showMetadataTab = computed(() => !!props.versionValidationErrors.length);
const showAssetsTab = computed(() => !!Object.keys(props.assetValidationErrors));

function getValidationErrorIcon(errorField: string): string {
  const icons = Object.keys(VALIDATION_ICONS).filter((field) => errorField.includes(field));
  if (icons.length > 0) {
    return (VALIDATION_ICONS as any)[icons[0]];
  }
  return VALIDATION_ICONS.DEFAULT;
}

</script>
