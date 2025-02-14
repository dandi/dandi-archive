<template>
  <v-container>
    <v-row
      v-if="dandiset.status === 'Pending'"
      class="my-2 px-1"
      no-gutters
    >
      <v-menu>
        <template #activator="{ props: menuProps }">
          <v-tooltip location="bottom">
            <template #activator="{ props: tooltipProps }">
              <v-card
                class="bg-amber-lighten-5 no-text-transform"
                variant="outlined"
                v-bind="{ ...menuProps, ...tooltipProps }"
              >
                <v-row class="align-center px-4">
                  <v-col
                    cols="1"
                    class="justify-center py-0"
                  >
                    <v-icon
                      color="warning"
                      class="mr-1"
                    >
                      mdi-playlist-remove
                    </v-icon>
                  </v-col>
                  <v-spacer />
                  <v-col cols="9">
                    <div class="text-caption">
                      Validation of the dandiset is pending.
                    </div>
                  </v-col>
                </v-row>
              </v-card>
            </template>
            <span>Reload the page to see if validation is over.</span>
          </v-tooltip>
        </template>
      </v-menu>
    </v-row>

    <!-- Dialog where version and asset errors are shown -->
    <v-dialog v-model="errorDialogOpen">
      <ValidationErrorDialog
        :selected-tab="selectedTab"
        :asset-validation-errors="dandiset.asset_validation_errors"
        :version-validation-errors="dandiset.version_validation_errors"
        :owner="isOwner"
      />
    </v-dialog>

    <!-- Version Validation Errors Button -->
    <v-card
      v-if="dandiset.version_validation_errors.length"
      class="my-2 px-1 bg-amber-lighten-5 no-text-transform"
      variant="outlined"
      @click="openErrorDialog('metadata')"
    >
      <v-row class="align-center px-4">
        <v-col
          cols="1"
          class="justify-center py-0"
        >
          <v-icon
            color="warning"
            class="mr-1"
          >
            mdi-playlist-remove
          </v-icon>
        </v-col>
        <v-spacer />
        <v-col cols="9">
          <div class="text-caption">
            This Dandiset has {{ dandiset.version_validation_errors.length }}
            metadata validation error(s).
          </div>
        </v-col>
      </v-row>
    </v-card>

    <!-- Asset Validation Errors Button -->
    <v-card
      v-if="numAssetValidationErrors"
      class="my-2 px-1 bg-amber-lighten-5 no-text-transform"
      variant="outlined"
      @click="openErrorDialog('assets')"
    >
      <v-row class="align-center px-4">
        <v-col
          cols="1"
          class="justify-center py-0"
        >
          <v-icon
            color="warning"
            class="mr-1"
          >
            mdi-database-remove
          </v-icon>
        </v-col>
        <v-spacer />
        <v-col cols="9">
          <div class="text-caption">
            This Dandiset has {{ numAssetValidationErrors }}
            asset validation error(s).
          </div>
        </v-col>
      </v-row>
    </v-card>
  </v-container>
</template>

<script setup lang="ts">
import { computed, defineProps, ref} from 'vue';
import type { PropType } from 'vue';

import ValidationErrorDialog from '@/components/DLP/ValidationErrorDialog.vue';
// import { open as meditorOpen } from '@/components/Meditor/state';
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

// function openMeditor() {
//   errorDialogOpen.value = false;
//   // meditorOpen.value = true;
// }
</script>
