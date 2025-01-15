<template>
  <v-card
    v-if="currentDandiset"
    outlined
    class="mt-4 px-3"
  >
    <v-dialog v-model="showUploadManagementDialog" max-width="60vw">
      <v-card class="pb-3">
        <v-card-title class="text-h5 font-weight-light">
          This dandiset has active uploads
        </v-card-title>
        <v-divider class="my-3" />
        <v-card-text>
          This dandiset has <strong>{{ incompleteUploads.length }}</strong> active uploads. Unembargo may not proceed until these are addressed. You may delete these uploads using the "Clear Uploads" button below.
        </v-card-text>

        <v-data-table
          height="40vh"
          :items-per-page="-1"
          :items="incompleteUploads"
          :headers="uploadHeaders"
          hide-default-footer
        >
          <template #item.created="{ item }">
            {{ formatDate(item.created, 'LLL') }}
          </template>
          <template #item.size="{ item }">
            {{ filesize(item.size, { round: 1, base: 10, standard: 'iec' }) }}
          </template>
        </v-data-table>

        <v-card-actions>
          <v-spacer />
          <v-btn
            depressed
            @click="showUploadManagementDialog = false"
          >
            Close
          </v-btn>

          <v-menu offset-y bottom>
            <template #activator="{ on, attrs }">
              <v-btn
                class="ml-2"
                depressed
                v-on="on"
                v-bind="attrs"
                primary
              >
                Clear Uploads
              </v-btn>
            </template>

            <v-card width="15vw">
              <v-card-text>
                Delete all uploads? Once deleted, any partially uploaded data will be lost.
              </v-card-text>
              <v-card-actions>
                <v-btn @click="clearUploads" color="error" depressed>Delete</v-btn>
              </v-card-actions>
            </v-card>
          </v-menu>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-dialog
      v-if="showWarningDialog"
      v-model="showWarningDialog"
      persistent
      max-width="60vh"
    >
      <v-card class="pb-3">
        <v-card-title class="text-h5 font-weight-light">
          Unembargo Dandiset
        </v-card-title>
        <v-divider class="my-3" />
        <v-card-text>
          <span>
            This action will unembargo this dandiset. Note that this is a
            <span class="font-weight-bold">
              permanent
            </span>
            action and cannot be undone. Once a dandiset has been unembargoed,
            it cannot be re-embargoed.
            <br><br>
            Note: this may take several days to complete.
          </span>
        </v-card-text>
        <v-card-text>
          Please enter this dandiset's identifier (
          <span class="font-weight-bold">
            {{ currentDandiset.dandiset.identifier }}
          </span>
          ) to proceed:
          <v-text-field
            v-model="confirmationPhrase"
            style="width: 30%;"
            dense
            outlined
          />
        </v-card-text>

        <v-card-actions>
          <v-btn
            color="error"
            depressed
            :disabled="confirmationPhrase !== currentDandiset.dandiset.identifier"
            @click="unembargo()"
          >
            Yes
          </v-btn>
          <v-btn
            depressed
            @click="showWarningDialog = false"
          >
            No, take me back
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-row
      class="mb-4"
      no-gutters
    >
      <v-tooltip left :disabled="!unembargo_in_progress">
        <template #activator="{ on }">
          <div
            class="px-1 pt-3"
            style="width: 100%"
            v-on="on"
          >
            <v-btn
              block
              :color="unembargoDisabled ? 'grey lighten-2': 'info'"
              depressed
              :disabled="unembargo_in_progress"
              @click="unembargoDisabled ? showUploadManagementDialog = true : unembargo()"
            >
              {{ unembargo_in_progress ? 'Unembargoing' : 'Unembargo' }}
              <v-spacer />
              <v-icon v-if="unembargoDisabled">mdi-alert</v-icon>
              <v-icon v-else>mdi-lock-open</v-icon>
            </v-btn>
          </div>
        </template>
        <span>This dandiset is being unembargoed, please wait.</span>
      </v-tooltip>
    </v-row>

    <DandisetValidationErrors :dandiset="currentDandiset" :isOwner="true" />

    <v-row>
      <v-subheader class="mb-2 black--text text-h5">
        This Version
      </v-subheader>
    </v-row>
    <v-row
      class="pa-2 mb-5 text-body-2 align-center"
      style="border-top: thin solid rgba(0, 0, 0, 0.12);
             border-bottom: thin solid rgba(0, 0, 0, 0.12);
             text-align: center;"
    >
      <v-col
        :cols="isMdDisplay ? 12 : 4"
        style=""
      >
        {{ formatDate(currentDandiset.modified) }}
      </v-col>
      <v-col>
        <h3>{{ currentDandiset.version.toUpperCase() }}</h3>
      </v-col>
    </v-row>
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import moment from 'moment';
import { dandiRest } from '@/rest';
import { useDandisetStore } from '@/stores/dandiset';
import type { IncompleteUpload } from '@/types';
import DandisetValidationErrors from './DandisetValidationErrors.vue';
import { filesize } from 'filesize';
import { useDisplay } from 'vuetify';

function formatDate(date: string, format: string = 'll'): string {
  return moment(date).format(format);
}

const uploadHeaders = [
  {
    text: 'Started at',
    value: 'created',
  },
  {
    text: 'Size',
    value: 'size',
  },
  {
    text: 'E-Tag',
    value: 'etag',
  },
];

const store = useDandisetStore();
const display = useDisplay();

const isMdDisplay = computed(() => display.md.value);
const currentDandiset = computed(() => store.dandiset);
const unembargo_in_progress = computed(() => currentDandiset.value?.dandiset.embargo_status === 'UNEMBARGOING');
const showWarningDialog = ref(false);
const confirmationPhrase = ref('');

// Upload management
const showUploadManagementDialog = ref(false);
const incompleteUploads = ref<IncompleteUpload[]>([]);
const unembargoDisabled = computed(() => !!(unembargo_in_progress.value || currentDandiset.value === null || currentDandiset.value.active_uploads));
if (unembargoDisabled.value) {
  fetchIncompleteUploads();
}

async function fetchIncompleteUploads() {
  incompleteUploads.value = await dandiRest.uploads(currentDandiset.value!.dandiset.identifier);
}

async function clearUploads() {
  const identifier = currentDandiset.value!.dandiset.identifier;
  await dandiRest.clearUploads(identifier);
  showUploadManagementDialog.value = false;

  store.fetchDandiset({ identifier, version: 'draft' });
}

async function unembargo() {
  if (currentDandiset.value) {
    // Display the warning dialog before releasing
    if (!showWarningDialog.value) {
      showWarningDialog.value = true;
      return;
    }

    await dandiRest.unembargo(currentDandiset.value.dandiset.identifier);

    // re-fetch the dandiset to refresh the embargo_status
    store.fetchDandiset({
      identifier: currentDandiset.value.dandiset.identifier,
      version: currentDandiset.value.version,
    });

    showWarningDialog.value = false;
  }
}
</script>
