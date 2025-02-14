<template>
  <v-card
    min-height="90vh"
    class="pa-2"
  >
    <v-tabs v-model="tab">
      <v-tab v-if="showMetadataTab">
        Metadata
      </v-tab>
      <v-tab v-if="showAssetsTab">
        Assets
      </v-tab>
    </v-tabs>
    <v-tabs-window v-model="tab">
      <!-- Metadata -->
      <v-tabs-window-item
        v-if="showMetadataTab"
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
              <v-list-item icon>
                <v-icon>
                  {{ getValidationErrorIcon(error.field) }}
                </v-icon>
              </v-list-item>

              <template v-if="error.field">
                {{ error.field }}:
              </template>
              {{ error.message }}
            </v-list-item>
            <v-divider />
          </div>
        </v-list>
      </v-tabs-window-item>

      <!-- Assets -->
      <v-tabs-window-item
        v-if="showAssetsTab"
        value="assets"
        :transition="false"
      >
        <v-list
          class="overflow-y-auto"
        >
          <v-expansion-panels multiple>
            <template
              v-for="(errors, path) in groupedAssetValidationErrors"
              :key="path"
            >
              <v-list-item>
                <v-list-item icon>
                  <v-icon>
                    <template v-if="errors.length > 1">
                      mdi-alert-plus
                    </template>
                    <template v-else>
                      {{ getValidationErrorIcon(errors[0].field) }}
                    </template>
                  </v-icon>
                </v-list-item>

                <!-- Inline single errors -->
                <template v-if="errors.length === 1">
                  <strong>{{ path }}</strong>
                  <template v-if="errors[0].field">
                    {{ errors[0].field }} -
                  </template>
                  {{ errors[0].message }}
                </template>

                <!-- Group multiple asset errors -->
                <template v-else>
                  <v-list-group class="multi-error-list-group">
                    <template #activator>
                      <strong>{{ path }}</strong>
                      <v-list-item-subtitle>Click to expand</v-list-item-subtitle>
                    </template>

                    <v-list-item
                      v-for="error in errors"
                      :key="`${error.field}-${error.message}`"
                    >
                      <v-list-item icon>
                        <v-icon>
                          {{ getValidationErrorIcon(error.field) }}
                        </v-icon>
                      </v-list-item>

                      <template v-if="error.field">
                        {{ error.field }}:
                      </template>
                      {{ error.message }}
                    </v-list-item>
                  </v-list-group>
                </template>
              </v-list-item>
            </template>
          </v-expansion-panels>
        </v-list>
      </v-tabs-window-item>
    </v-tabs-window>
  </v-card>
</template>

<script setup lang="ts">
import type { ValidationError } from '@/types';
import type { PropType } from 'vue';
import { watch, computed, ref } from 'vue';

import { VALIDATION_ICONS } from '@/utils/constants';

const props = defineProps({
  assetValidationErrors: {
    type: Array as PropType<ValidationError[]>,
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
const showAssetsTab = computed(() => !!Object.keys(props.assetValidationErrors).length);
const groupedAssetValidationErrors = computed(() => {
  const path_asset_map: Record<string, ValidationError[]> = {};
  props.assetValidationErrors.forEach((err) => {
    if (!(err.path in path_asset_map)) {
      path_asset_map[err.path] = [];
    }
    path_asset_map[err.path].push(err);
  });

  return path_asset_map;
});

function getValidationErrorIcon(errorField: string): string {
  const icons = Object.keys(VALIDATION_ICONS).filter((field) => errorField.includes(field));
  if (icons.length > 0) {
    return (VALIDATION_ICONS as any)[icons[0]];
  }
  return VALIDATION_ICONS.DEFAULT;
}

</script>
<style>
.multi-error-list-group .v-list-group__header {
  padding-left: 0;
  padding-right: 0;
}
</style>
