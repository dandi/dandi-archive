<template>
  <div>
    <v-card
      v-if="currentDandiset && otherVersions"
      class="rounded-0 elevation-0"
    >
      <v-dialog
        v-if="showPublishWarningDialog"
        v-model="showPublishWarningDialog"
        persistent
        max-width="60vh"
      >
        <v-card class="pb-3">
          <v-card-title class="text-h5 font-weight-light">
            WARNING
          </v-card-title>
          <v-divider class="my-3" />
          <v-card-text>
            This action will force publish this Dandiset, potentially
            before the owners are prepared to do so.
          </v-card-text>
          <v-card-text>
            Would you like to proceed?
          </v-card-text>

          <v-card-actions>
            <v-btn
              color="error"
              variant="flat"
              @click="publish()"
            >
              Yes
            </v-btn>
            <v-btn
              variant="flat"
              @click="showPublishWarningDialog = false"
            >
              No, take me back
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
      <v-card-text
        v-if="!publishButtonHidden"
        class="pb-2"
      >
        <v-tooltip
          :disabled="!publishDisabledMessage"
          location="left"
        >
          <template #activator="{ props: tooltipProps }">
            <div v-bind="tooltipProps">
              <v-row
                v-if="showPublishWarning"
                class="text-caption text-error align-center mb-3"
                no-gutters
              >
                <v-col
                  cols="1"
                  class="mr-2"
                >
                  <v-icon color="error">
                    mdi-alert-circle
                  </v-icon>
                </v-col>
                <v-col>
                  <span>
                    As an <span class="font-weight-bold">admin</span>,
                    you may publish Dandisets without being an owner.
                  </span>
                </v-col>
              </v-row>
              <div class="text-center">
                <v-dialog
                  v-model="showPublishChecklistDialog"
                  width="900"
                >
                  <template #activator="{ props: dialogProps }">
                    <v-btn
                      block
                      :color="showPublishWarning ? 'error' : 'success'"
                      class="justify-start"
                      variant="flat"
                      :disabled="publishButtonDisabled"
                      prepend-icon="mdi-upload"
                      v-bind="dialogProps"
                    >
                      Publish
                    </v-btn>
                  </template>

                  <v-card>
                    <v-card-title class="text-h5 bg-grey-lighten-2">
                      Publish Checklist
                    </v-card-title>

                    <v-card-text>
                      <v-list>
                        <span class="text-body-1 font-weight-bold">
                          For best results, please check the following
                          items before you publish:
                        </span>
                        <!-- Note: this is safe as we aren't rendering any user-generated input -->
                        <!-- eslint-disable vue/no-v-html vue/no-v-text-v-html-on-component -->
                        <v-list-item
                          v-for="(item, i) in PUBLISH_CHECKLIST"
                          :key="`checklist_item_${i}`"
                          class="text-body-2 my-1"
                          v-html="`<span>${i+1}. ${item}</span>`"
                        />
                        <!-- eslint-enable vue/no-v-html vue/no-v-text-v-html-on-component -->
                      </v-list>
                    </v-card-text>

                    <v-divider />

                    <v-card-actions class="justify-end">
                      <v-btn
                        color="dropzone"
                        variant="flat"
                        @click="showPublishChecklistDialog = false"
                      >
                        Cancel
                      </v-btn>
                      <v-btn
                        :color="showPublishWarning ? 'error' : 'success'"
                        variant="flat"
                        @click="publish"
                      >
                        Publish
                        <v-spacer />
                        <v-progress-circular
                          v-if="publishing"
                          indeterminate
                        />
                        <v-icon v-else>
                          mdi-upload
                        </v-icon>
                      </v-btn>
                    </v-card-actions>
                  </v-card>
                </v-dialog>
              </div>
            </div>
          </template>
          <span>{{ publishDisabledMessage }}</span>
        </v-tooltip>
      </v-card-text>

      <DandisetValidationErrors
        :dandiset="currentDandiset"
        :is-owner="isOwner"
      />

    </v-card>
    <v-divider />
    <v-card class="rounded-0 elevation-0">
      <v-card-title>
        This Version
      </v-card-title>
      <v-card-text>
        <v-list class="pa-0">
          <v-list-item class="border rounded">
            <template v-slot:prepend>
              <v-icon color="green">mdi-check-bold</v-icon>
            </template>
            <div class="d-flex align-center justify-space-between">
              <v-list-item-title>
                <strong>{{ currentVersion?.toUpperCase() }}</strong>
              </v-list-item-title>
              <v-list-item-subtitle class="text-caption">{{ formatDate(currentDandiset.modified) }}</v-list-item-subtitle>
            </div>
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>
    <v-divider />
    <v-card class="rounded-0 elevation-0">
      <v-card-title>
        Other Versions
      </v-card-title>
      <v-card-text>
        <v-empty-state
          v-if="!otherVersions.length"
          text="This is the only version. When other versions get published, they'll appear here."
        ></v-empty-state>
        <v-list
          v-else
          class="border border-b-0 rounded pa-0"
        >
          <v-list-item
            v-for="(version, i) in otherVersions"
            :key="i"
            class="border-b pl-2"
          >
            <template v-slot:prepend>
              <v-list-item-action>
                <v-tooltip
                  location="start"
                  text="Check out this version"
                >
                  <template v-slot:activator="{ props }">
                    <v-btn
                      v-bind="props"
                      size="x-small"
                      variant="outlined"
                      icon="mdi-source-branch"
                      class="rounded"
                      @click="setVersion(version)"
                    ></v-btn>
                  </template>
                </v-tooltip>
              </v-list-item-action>
            </template>
            <div class="d-flex align-center justify-space-between pl-4">
              <v-list-item-title>{{ version.version.toUpperCase() }}</v-list-item-title>
              <v-list-item-subtitle class="text-caption">{{ formatDate(version.modified) }}</v-list-item-subtitle>
            </div>
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>

      <v-snackbar :model-value="!!alreadyBeingPublishedError">
        This dandiset is already being published. Please wait for publishing to complete.
      </v-snackbar>
      <v-snackbar :model-value="!!publishedVersion">
        Publish complete.
        <template #actions>
          <v-btn
            color="info"
            variant="text"
            @click="navigateToPublishedVersion"
          >
            Go to published dandiset
          </v-btn>
        </template>
      </v-snackbar>
  </div>
</template>

<script setup lang="ts">
import type { ComputedRef } from 'vue';
import {
  onUnmounted,
  onMounted,
  computed,
  ref,
  watchEffect,
} from 'vue';
import { useDisplay } from 'vuetify';

import axios from 'axios';
import moment from 'moment';

import type { RouteLocationRaw } from 'vue-router';
import { useRoute } from 'vue-router';

import { dandiRest, loggedIn as loggedInFunc, user } from '@/rest';
import { useDandisetStore } from '@/stores/dandiset';
import router from '@/router';
import type { User, Version } from '@/types';
import { draftVersion } from '@/utils/constants';
import DandisetValidationErrors from './DandisetValidationErrors.vue';


const PUBLISH_CHECKLIST = [
  'A descriptive title (e.g., <span class="font-italic">Data related to foraging behavior in bees</span> rather than <span class="font-italic">Smith et al 2022</span>)',
  'A clear, informative description that is helpful for other neuroscientists',
  'A reference to a protocol in protocols.io detailing how you collected the data (this can also be another publication added as a resource)',
  'A reference to an ethics protocol number if you are working with an Institutional Review Board on this study',
  'Funding information (DANDI treats funding agencies as contributors, so you can add multiple contributing institutions as needed. If you are the funder, you can add a new contributor of type "organization", uncheck "include contributor in citation", set the role as "dcite:Funder", and include the relevant award information)',
  'References to code in GitHub, related publications, etc.',
];

// Sort versions from most recently modified to least recently modified.
// The DRAFT version is always the first element when present.
function sortVersions(v1: Version, v2: Version): number {
  // Always put draft first
  if (v1.version === draftVersion || v1.modified > v2.modified) {
    return -1;
  }
  if (v1.modified < v2.modified) {
    return 1;
  }
  return 0;
}

const props = defineProps({
  userCanModifyDandiset: {
    type: Boolean,
    required: true,
  },
});
const route = useRoute();
const store = useDandisetStore();
const display = useDisplay();

const isMdDisplay = computed(() => display.md.value);
const currentDandiset = computed(() => store.dandiset);
const currentVersion = computed(() => store.dandiset?.version);

const otherVersions: ComputedRef<Version[]|undefined> = computed(
  () => store.versions?.filter(
    (version: Version) => version.version !== currentVersion.value,
  ).sort(sortVersions),
);

const loggedIn: ComputedRef<boolean> = computed(loggedInFunc);

const isOwner: ComputedRef<boolean> = computed(
  () => !!(store.owners?.find(
    (owner: User) => owner.username === user.value?.username,
  )),
);

// true if the dandiset is being published due to the user
// clicking the publish button on this page
const publishing = ref(false);
// The version that resulted from the recent publish, if applicable
const publishedVersion = ref('');

const alreadyBeingPublishedError = ref(false);

const containsZarr = ref(false);
watchEffect(async () => {
  if (currentDandiset.value) {
    const { identifier } = currentDandiset.value.dandiset;
    const { version } = currentDandiset.value;
    const res = await dandiRest.assets(
      identifier,
      version,
      { params: { zarr: true, page_size: 1 } },
    );

    containsZarr.value = res !== null && res.count > 0;
  }
});

const publishDisabledMessage: ComputedRef<string> = computed(() => {
  if (!loggedIn.value) {
    return 'You must be logged in to edit.';
  }
  if ((isOwner.value || user.value?.admin) && currentVersion.value !== draftVersion) {
    return 'Only draft versions can be published.';
  }
  if (!props.userCanModifyDandiset && !user.value?.admin) {
    return 'You do not have permission to edit this dandiset.';
  }
  if (currentDandiset.value?.status === 'Pending') {
    return 'This dandiset has not yet been validated.';
  }
  if (currentDandiset.value?.status === 'Validating') {
    return 'Currently validating this dandiset.';
  }
  if (currentDandiset.value?.status === 'Published') {
    return 'No changes since last publish.';
  }
  if (currentDandiset.value?.dandiset.embargo_status === 'UNEMBARGOING') {
    return 'This dandiset is being unembargoed, please wait.';
  }
  if (publishing.value) {
    return 'This dandiset is being published, please wait.';
  }
  if (containsZarr.value) {
    return 'Dandisets containing Zarr archives cannot currently be published.';
  }
  return '';
});

let timer: number | undefined;
onMounted(() => {
  timer = window.setInterval(async () => {
  // When a dandiset is being published, poll the server to check if it's finished
    if (publishing.value && currentDandiset.value) {
      const { identifier } = currentDandiset.value.dandiset!;
      const { version } = currentDandiset.value;
      const dandiset = await dandiRest.specificVersion(identifier, version);

      if (dandiset?.status === 'Published') {
      // re-fetch current dandiset so it includes the newly published version
        await store.fetchDandiset({ identifier, version });
        await store.fetchDandisetVersions({ identifier });

        publishedVersion.value = otherVersions.value![0].version;

        publishing.value = false;
      }
    }
  }, 2000);
});
onUnmounted(() => {
  if (timer === undefined) {
    throw Error('Invalid timer value');
  }
  window.clearInterval(timer);
});



const publishButtonDisabled = computed(() => !!(
  currentDandiset.value?.version_validation_errors.length
      || currentDandiset.value?.asset_validation_errors.length
      || currentDandiset.value?.dandiset.embargo_status !== 'OPEN'
      || publishDisabledMessage.value
));

const publishButtonHidden: ComputedRef<boolean> = computed(() => {
  if (!store.owners) {
    return true;
  }
  // always show the publish button to admins
  if (user.value?.admin) {
    return false;
  }
  // otherwise, only show it when the logged in user is an owner
  return !isOwner.value;
});

// Show warning message above publish button if user
// is an admin but not an owner of the dandiset
const showPublishWarning: ComputedRef<boolean> = computed(
  () => !!(!publishButtonDisabled.value && user.value?.admin && !isOwner.value),
);

const showPublishWarningDialog = ref(false);

const showPublishChecklistDialog = ref(false);

function formatDate(date: string): string {
  return moment(date).format('ll');
}

function setVersion({ version: newVersion }: any) {
  const version = newVersion || draftVersion;

  const identifier = currentDandiset.value?.dandiset.identifier;

  if (!identifier) {
    return;
  }

  if (route.params.version !== version) {
    router.replace({
      ...route,
      params: {
        ...route.params,
        version,
      },
    } as RouteLocationRaw);

    store.fetchDandiset({
      identifier: currentDandiset.value?.dandiset.identifier,
      version: newVersion,
    });
  }
}

async function publish() {
  if (currentDandiset.value) {
    // If user is an admin but not an owner, display the warning dialog before publishing
    if (showPublishWarning.value && !showPublishWarningDialog.value) {
      showPublishWarningDialog.value = true;
      return;
    }

    showPublishChecklistDialog.value = false;
    showPublishWarningDialog.value = false;

    publishing.value = true;
    try {
      const { version } = await dandiRest.publish(currentDandiset.value.dandiset.identifier);
      publishedVersion.value = version;
    } catch (e) {
      // A 423: Locked error means that the dandiset is currently undergoing publishing.
      // If that happens, display an error.
      if (axios.isAxiosError(e) && e.response?.status === 423) {
        alreadyBeingPublishedError.value = true;
      } else {
        throw e;
      }
    }
  }
}

function navigateToPublishedVersion() {
  const { identifier } = currentDandiset.value!.dandiset;
  const version = publishedVersion.value;

  // reset these for the new version
  publishing.value = false;
  publishedVersion.value = '';

  // navigate to the newly published version
  router.push({
    name: 'dandisetLanding',
    params: { identifier, version },
  });
}

</script>
