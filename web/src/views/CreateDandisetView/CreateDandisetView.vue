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
                max-width="25%"
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
                  elapsed. Uploading data to the DANDI Archive under embargo requires a relevant
                  NIH award number, and the data will be automatically published when the embargo
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
              href="https://docs.dandiarchive.org/35_data_licenses/"
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
            NIH Award Number
          </div>
          <div>
            Provide an NIH award number for this embargoed Dandiset. Note: this
            can be changed at any time and additional award numbers can be added
            later.
          </div>
          <v-text-field
            v-model="awardNumber"
            label="Award number"
            :counter="120"
            :required="embargoed"
            variant="outlined"
            density="compact"
            class="my-4"
            :rules="awardNumberRules"
          />
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

import type { IdentifierForAnAward, LicenseType, License } from '@/types';

// Regular expression to validate an NIH award number.
// Based on https://era.nih.gov/files/Deciphering_NIH_Application.pdf
// and https://era.nih.gov/erahelp/commons/Commons/understandGrantNums.htm
const NIH_AWARD_REGEX = /^\d \w+ \w{2} \d{6}-\d{2}([A|S|X|P]\d)?$/;

function awardNumberValidator(awardNumber: IdentifierForAnAward): boolean {
  return NIH_AWARD_REGEX.test(awardNumber);
}

const VALIDATION_FAIL_MESSAGE = 'Award number must be properly space-delimited.\n\nExample (exclude quotes):\n"1 R01 CA 123456-01A1"';

const router = useRouter();
const store = useDandisetStore();

const name = ref('');
const description = ref('');
const license = ref<LicenseType>();
const embargoed = ref(false);
const awardNumber = ref('');
const saveDisabled = computed(
  () => !name.value
      || !description.value
      || (embargoed.value && !awardNumberValidator(awardNumber.value))
      || (!embargoed.value && !license.value),
);

const awardNumberRules = computed(
  () => [(v: string) => awardNumberValidator(v) || VALIDATION_FAIL_MESSAGE],
);

const nameMaxLength: ComputedRef<number> = computed(() => store.schema.properties.name.maxLength);
const descriptionMaxLength: ComputedRef<number> = computed(
  () => store.schema.properties.description.maxLength,
);
const dandiLicenses: ComputedRef<LicenseType[]> = computed(
  () => store.schema.$defs.LicenseType.enum,
);

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

  const { data } = embargoed.value
    ? await dandiRest.createEmbargoedDandiset(name.value, metadata, awardNumber.value)
    : await dandiRest.createDandiset(name.value, metadata);
  const { identifier } = data;
  router.push({ name: 'dandisetLanding', params: { identifier } });
}

</script>
