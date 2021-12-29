<template>
  <v-card v-page-title="'Create Dandiset'">
    <v-card-title>
      <span class="text-h5">Register a new dataset</span>
    </v-card-title>
    <v-card-text class="my-3">
      <v-form>
        <v-text-field
          v-model="name"
          label="Name*"
          hint="Provide a title for this dataset"
          persistent-hint
          :counter="120"
          required
          outlined
        />
        <v-textarea
          v-model="description"
          label="Description*"
          hint="Provide a description for this dataset"
          :counter="3000"
          persistent-hint
          required
          outlined
          class="my-4"
        />
        <v-checkbox
          v-model="embargoed"
          hide-details
          class="shrink mr-2 mt-0"
        >
          <template #label>
            Embargo this dataset?
          </template>
        </v-checkbox>
        <v-text-field
          v-if="embargoed"
          v-model="awardNumber"
          label="Award number*"
          hint="Provide an NIH award number for this embargoed dataset"
          persistent-hint
          :counter="120"
          :required="embargoed"
          outlined
          class="mt-4 shrink"
          style="width: 20vw;"
          :rules="awardNumberRules"
        />
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

<script lang="ts">
import { defineComponent, computed, ref } from '@vue/composition-api';
import { dandiRest, loggedIn } from '@/rest';
import { IdentifierForAnAward } from '@/types/schema';

// Regular expression to validate an NIH award number.
// Based on https://era.nih.gov/files/Deciphering_NIH_Application.pdf
// and https://era.nih.gov/erahelp/commons/Commons/understandGrantNums.htm
const NIH_AWARD_REGEX = /^\d \w+ \w{2} \d{6}-\d{2}([A|S|X|P]\d)?$/;

function awardNumberValidator(awardNumber: IdentifierForAnAward): boolean {
  return NIH_AWARD_REGEX.test(awardNumber);
}

const VALIDATION_FAIL_MESSAGE = 'Award number must be properly space-delimited.\n\nExample (exclude quotes):\n"1 R01 CA 123456-01A1"';

export default defineComponent({
  name: 'CreateDandisetView',
  setup(props, ctx) {
    const name = ref('');
    const description = ref('');
    const embargoed = ref(false);
    const awardNumber = ref('');
    const saveDisabled = computed(
      () => !name.value
      || !description.value
      || (embargoed.value && !awardNumberValidator(awardNumber.value)),
    );

    const awardNumberRules = computed(
      () => [(v: string) => awardNumberValidator(v) || VALIDATION_FAIL_MESSAGE],
    );

    if (!loggedIn()) {
      ctx.root.$router.push({ name: 'home' });
    }

    async function registerDandiset() {
      const metadata = { name: name.value, description: description.value };

      const { data } = embargoed.value
        ? await dandiRest.createEmbargoedDandiset(name.value, metadata, awardNumber.value)
        : await dandiRest.createDandiset(name.value, metadata);
      const { identifier } = data;
      ctx.root.$router.push({ name: 'dandisetLanding', params: { identifier } });
    }

    return {
      name,
      description,
      embargoed,
      awardNumber,
      saveDisabled,
      registerDandiset,
      awardNumberRules,
      awardNumberValidator,
    };
  },
});

</script>
