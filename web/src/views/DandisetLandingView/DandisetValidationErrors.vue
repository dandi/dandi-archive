<template>
  <v-container class="pt-1">
    <v-menu v-if="dandiset.status === 'Pending'">
      <template #activator="{ props: menuProps }">
        <v-tooltip location="bottom">
          <template #activator="{ props: tooltipProps }">
            <v-alert
              class="my-1"
              density="compact"
              icon="mdi-playlist-remove"
              type="warning"
              variant="tonal"
              v-bind="{ ...menuProps, ...tooltipProps }"
            >
              <v-alert-content class="text-body-2">
                Validation of the dandiset is pending.
              </v-alert-content>
            </v-alert>
          </template>
          <span>Reload the page to see if validation is over.</span>
        </v-tooltip>
      </template>
    </v-menu>

    <!-- Dialog where version and asset errors are shown -->
    <v-dialog v-model="errorDialogOpen">
      <ValidationErrorDialog
        :selected-tab="selectedTab"
        :asset-validation-errors="dandiset.asset_validation_errors"
        :version-validation-errors="dandiset.version_validation_errors"
        :owner="isOwner"
        @open-meditor="openMeditor"
      />
    </v-dialog>

    <!-- Version Validation Errors Button -->
    <v-alert
      v-if="dandiset.version_validation_errors.length"
      class="my-1"
      density="compact"
      icon="mdi-playlist-remove"
      type="warning"
      variant="tonal"
      @click="openErrorDialog('metadata')"
    >
      <v-alert-content class="text-body-2">
        This Dandiset has {{ dandiset.version_validation_errors.length }} metadata validation error(s).
      </v-alert-content>
    </v-alert>

    <!-- Asset Validation Errors Button -->
    <v-alert
      v-if="numAssetValidationErrors"
      class="my-1"
      density="compact"
      icon="mdi-database-remove"
      type="warning"
      variant="tonal"
      @click="openErrorDialog('assets')"
    >
      <v-alert-content class="text-body-2">
        This Dandiset has {{ numAssetValidationErrors }} asset validation error(s).
      </v-alert-content>
    </v-alert>
  </v-container>
</template>

<script setup lang="ts">
import { computed, ref} from 'vue';
import type { PropType } from 'vue';

import ValidationErrorDialog from '@/components/DLP/ValidationErrorDialog.vue';
import { open as meditorOpen } from '@/components/Meditor/state';
import type { Version } from '@/types';

const props = defineProps({
  dandiset: {
    type: Object as PropType<Version>,
      required: true,
  },
  isOwner: {
    type: Boolean as PropType<boolean>,
    required: true,
  },
});

const numAssetValidationErrors = computed(() => props.dandiset.asset_validation_errors.length);

// Error dialog
const errorDialogOpen = ref(false);
type ErrorCategory = 'metadata' | 'assets';
const selectedTab = ref<ErrorCategory>('metadata');
function openErrorDialog(tab: ErrorCategory) {
  errorDialogOpen.value = true;
  selectedTab.value = tab;
}

function openMeditor() {
  errorDialogOpen.value = false;
  meditorOpen.value = true;
}
</script>
