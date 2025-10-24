<template>
  <v-card v-page-title="'Create Dandiset'">
    <v-card-title>
      <span class="text-h3">Register a new Dandiset</span>
    </v-card-title>
    <v-card-text class="my-3">
      <v-form>
        <div>
          <v-switch
            v-model="embargoed"
          >
            <template #label>
              Embargo this Dandiset
              <v-tooltip
                location="right"
                width="30vw"
              >
                <template #activator="{ props }">
                  <div
                    style="cursor: help"
                    v-bind="props"
                  >
                    <small class="ml-3 d-flex align-center">
                      (What is this?)
                      <v-icon size="small">
                        mdi-information
                      </v-icon>
                    </small>
                  </div>
                </template>
                <span>
                  Embargoed Dandisets are hidden from public access until a specific time period has
                  elapsed. You can associate the dandiset with a research award/grant or set a
                  2-year embargo period. The data will be automatically published when the embargo
                  period expires.
                </span>
              </v-tooltip>
            </template>
          </v-switch>
        </div>
        <div class="text-h4">
          Title
        </div>
        <div>
          Provide a title for this Dandiset. The title will appear in search
          results and at the top of the home page for this Dandiset, so make it
          concise and descriptive.
        </div>
        <v-text-field
          v-model="name"
          label="Title"
          :counter="nameMaxLength"
          required
          variant="outlined"
          density="compact"
          class="my-4"
        />
        <v-alert
          v-if="showTestWarning"
          type="warning"
          variant="tonal"
          class="my-2"
        >
          <span>
            If this is a test dandiset and does not contain actual neuroscience data,
            please consider using the sandbox instance instead. See documentation
            <a
              :href="sandboxDocsUrl"
              target="_blank"
            >here</a>
            for how to use the the sandbox instance.
          </span>
        </v-alert>

        <div class="text-h4">
          Description
        </div>
        <div>
          Provide a description for this Dandiset. This will appear prominently
          under the title in the home page for this Dandiset.
        </div>
        <v-textarea
          v-model="description"
          label="Description"
          :counter="descriptionMaxLength"
          required
          variant="outlined"
          density="compact"
          class="my-4"
        />
        <div v-if="!embargoed">
          <div class="text-h4">
            License
          </div>
          <div>
            Select a license under which to share the contents of this Dandiset.
            You can learn more about <a
              :href="`${dandiDocumentationUrl}/user-guide-sharing/data-licenses`"
              target="_blank"
              rel="noopener"
            >
              licenses for Dandisets
            </a>.
          </div>
          <v-select
            v-model="license"
            :items="dandiLicenses"
            label="License"
            class="my-4"
            variant="outlined"
            density="compact"
          />
        </div>
        <div v-else>
          <div class="text-h4">
            Award Information
          </div>
          <div>
            <v-switch
              v-model="hasAward"
              class="mb-4"
            >
              <template #label>
                This Dandiset is associated with a research award/grant
              </template>
            </v-switch>
          </div>

          <div v-if="hasAward">
            <div class="text-h5 mb-2">
              Funding Source
            </div>
            <div class="mb-3">
              Specify the funding organization for this research.
            </div>
            <v-text-field
              v-model="fundingSource"
              label="Funding source (e.g., National Institutes of Health)"
              required
              variant="outlined"
              density="compact"
              class="mb-4"
              :rules="fundingSourceRules"
            />

            <div class="text-h5 mb-2">
              Grant/Award Number
            </div>
            <div class="mb-3">
              Provide the grant or award number. For awards without a grant number, please
              provide the project name.
            </div>
            <v-text-field
              v-model="awardNumber"
              label="Grant/Award number"
              :counter="120"
              variant="outlined"
              density="compact"
              class="mb-4"
            />

            <div class="text-h5 mb-2">
              Grant End Date
            </div>
            <div class="mb-3">
              When does this grant/award period end? This will be used to determine the embargo end date.
            </div>
            <v-text-field
              v-model="grantEndDate"
              label="Grant end date"
              type="date"
              required
              variant="outlined"
              density="compact"
              class="mb-4"
              :rules="grantEndDateRules"
            />
          </div>

          <div v-else>
            <div class="text-h5 mb-2">
              Embargo End Date
            </div>
            <div class="mb-3">
              Since this Dandiset is not associated with a research award, the embargo will automatically end 2 years from today.
            </div>
            <v-text-field
              v-model="embargoEndDate"
              label="Embargo end date"
              readonly
              variant="outlined"
              density="compact"
              class="mb-4"
            />
          </div>
        </div>
        <small class="float-right font-weight-bold">All fields are required</small>
      </v-form>
    </v-card-text>
    <v-card-actions>
      <v-spacer />
      <v-btn
        type="submit"
        color="primary"
        :disabled="saveDisabled"
        variant="flat"
        @click="registerDandiset"
      >
        Register Dandiset
        <template #loader>
          <span>Registering...</span>
        </template>
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import type { ComputedRef } from 'vue';
import { dandiRest, loggedIn } from '@/rest';
import { useDandisetStore } from '@/stores/dandiset';
import { dandiDocumentationUrl, sandboxDocsUrl } from '@/utils/constants';

import type { LicenseType, License } from '@/types';

const router = useRouter();
const store = useDandisetStore();

const name = ref('');
const description = ref('');
const license = ref<LicenseType>();
const embargoed = ref(false);
const hasAward = ref(true);
const fundingSource = ref('');
const awardNumber = ref('');
const grantEndDate = ref('');

// Calculate embargo end date as 2 years from today
const embargoEndDate = computed(() => {
  const today = new Date();
  const twoYearsFromNow = new Date(today.getFullYear() + 2, today.getMonth(), today.getDate());
  return twoYearsFromNow.toISOString().split('T')[0];
});

// Helper function to validate grant end date bounds
const isGrantEndDateValid = computed(() => {
  if (!grantEndDate.value) return false; // Required field

  const selectedDate = new Date(grantEndDate.value);
  const today = new Date();
  const fiveYearsFromNow = new Date(today.getFullYear() + 5, today.getMonth(), today.getDate());

  // Check if date is in the past or more than 5 years in the future
  return selectedDate >= today && selectedDate <= fiveYearsFromNow;
});

const saveDisabled = computed(
  () => !name.value
      || !description.value
      || (!embargoed.value && !license.value)
      || (embargoed.value && hasAward.value && (!fundingSource.value || !grantEndDate.value || !isGrantEndDateValid.value))
      || (embargoed.value && !hasAward.value && !embargoEndDate.value),
);

const fundingSourceRules = computed(
  () => [(v: string) => !!v || 'Funding source is required'],
);

const grantEndDateRules = computed(() => [
  (v: string) => !!v || 'Grant end date is required',
  (v: string) => {
    if (!v) return true; // Skip validation if empty (handled by required rule)

    const selectedDate = new Date(v);
    const today = new Date();
    const fiveYearsFromNow = new Date(today.getFullYear() + 5, today.getMonth(), today.getDate());

    // Check if date is in the past
    if (selectedDate < today) {
      return 'Grant end date cannot be in the past';
    }

    // Check if date is more than 5 years in the future
    if (selectedDate > fiveYearsFromNow) {
      return 'DANDI only supports 5 years of embargo';
    }

    return true;
  },
]);

const nameMaxLength: ComputedRef<number> = computed(() => store.schema.properties.name.maxLength);
const descriptionMaxLength: ComputedRef<number> = computed(
  () => store.schema.properties.description.maxLength,
);
const dandiLicenses: ComputedRef<LicenseType[]> = computed(
  () => store.schema.$defs.LicenseType.enum,
);

// Try to guess if the Dandiset is a test Dandiset based on the name, and show a warning if so.
const showTestWarning = computed(() => name.value.toLowerCase().includes('test'));

if (!loggedIn()) {
  router.push({ name: 'home' });
}

async function registerDandiset() {
  const metadata: {name: string, description: string, license?: License} = {
    name: name.value,
    description: description.value,
  };

  if (license.value) {
    metadata.license = [license.value];
  }

  if (embargoed.value) {
    // Handle embargoed dandiset creation with new structure
    const embargoData = {
      hasAward: hasAward.value,
      funding_source: hasAward.value ? fundingSource.value : undefined,
      award_number: hasAward.value ? awardNumber.value : undefined,
      embargo_end_date: hasAward.value ? grantEndDate.value : embargoEndDate.value,
    };

    const { data } = await dandiRest.createEmbargoedDandiset(name.value, metadata, embargoData);
    const { identifier } = data;
    router.push({ name: 'dandisetLanding', params: { identifier } });
  } else {
    const { data } = await dandiRest.createDandiset(name.value, metadata);
    const { identifier } = data;
    router.push({ name: 'dandisetLanding', params: { identifier } });
  }
}

</script>
