<template>
  <v-card v-page-title="'Create Dandiset'">
    <v-card-title>
      <span class="text-h5">Register a new dataset</span>
    </v-card-title>
    <v-card-text class="my-3">
      <v-form>
        <h1>Dandiset Title</h1>
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
          outlined
        />

        <h1>Description</h1>
        <div>
          Provide a description for this Dandiset. This will appear prominently
          under the title in the home page for this Dandiset.
        </div>
        <v-textarea
          v-model="description"
          label="Description"
          :counter="descriptionMaxLength"
          required
          outlined
          class="my-4"
        />
        <div>
          <v-checkbox
            v-model="embargoed"
            hide-details
            class="shrink mr-2 mt-0"
          >
            <template #label>
              Embargo this dataset
              <v-tooltip
                right
                max-width="25%"
              >
                <template #activator="{ on, attrs }">
                  <div
                    v-bind="attrs"
                    style="cursor: help"
                    v-on="on"
                  >
                    <small class="ml-3 d-flex align-center">
                      (What is this?)
                      <v-icon small>
                        mdi-information
                      </v-icon>
                    </small>
                  </div>
                </template>
                <span>
                  Embargoed datasets are hidden from public access until a specific time period has
                  elapsed. Uploading data to the DANDI archive under embargo requires a relevant
                  NIH award number, and the data will be automatically published when the embargo
                  period expires.
                </span>
              </v-tooltip>
            </template>
          </v-checkbox>
          <v-text-field
            v-if="embargoed"
            v-model="awardNumber"
            label="Award number*"
            hint="Provide an NIH award number for this embargoed dataset.
                Note: this can be changed at any time and additional award
                numbers can be added later."
            persistent-hint
            :counter="120"
            :required="embargoed"
            outlined
            class="mt-4 shrink"
            style="width: 20vw;"
            :rules="awardNumberRules"
          />
        </div>
        <div v-if="!embargoed">
          <h1>License</h1>
          <div>
            Select a license under which to share the contents of this Dandiset.
            You can learn more about <a
              href="https://www.dandiarchive.org/handbook/35_data_licenses/"
              target="_blank" rel="noopener">licenses
            for Dandisets</a>.
          </div>
          <v-select
            v-model="license"
            :items="dandiLicenses"
            label="License"
            class="my-4"
            outlined
            dense
          />
        </div>
        <small class="float-right font-weight-bold">*indicates required field</small>
      </v-form>
    </v-card-text>
    <v-card-actions>
      <v-spacer />
      <v-btn
        type="submit"
        color="primary"
        :disabled="saveDisabled"
        depressed
        @click="registerDandiset"
      >
        Register dataset
        <template #loader>
          <span>Registering...</span>
        </template>
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { dandiRest, loggedIn } from '@/rest';
import { useDandisetStore } from '@/stores/dandiset';
import { useRouter } from 'vue-router/composables';

import type { ComputedRef } from 'vue';
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
  () => store.schema.definitions.LicenseType.enum,
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
