<template>
  <v-card v-page-title="'Create Dandiset'">
    <v-card-title>
      <span class="text-h5">Register a new dataset</span>
    </v-card-title>
    <v-card-text class="my-3">
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
      />
      <small class="float-right font-weight-bold">*indicates required field</small>
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

export default defineComponent({
  name: 'CreateDandisetView',
  setup(props, ctx) {
    const name = ref('');
    const description = ref('');
    const embargoed = ref(false);
    const awardNumber = ref('');
    const saveDisabled = computed(
      () => !name.value || !description.value || (embargoed.value && !awardNumber.value),
    );

    if (!loggedIn()) {
      ctx.root.$router.push({ name: 'home' });
    }

    async function registerDandiset() {
      const { data } = await dandiRest.createDandiset(
        name.value, description.value, embargoed.value, awardNumber.value,
      );
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
    };
  },
});

</script>
