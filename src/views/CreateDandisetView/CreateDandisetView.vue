<template>
  <v-card v-page-title="'Create Dandiset'">
    <v-card-title>
      <span class="text-h5">Register a new dataset</span>
    </v-card-title>
    <v-card-text>
      <v-text-field
        v-model="name"
        label="Name*"
        hint="Provide a title for this dataset"
        persistent-hint
        :counter="120"
        required
      />
      <v-textarea
        v-model="description"
        label="Description*"
        hint="Provide a description for this dataset"
        :counter="3000"
        persistent-hint
        required
      />
      <small>*indicates required field</small>
    </v-card-text>
    <v-card-actions>
      <v-spacer />
      <v-btn
        type="submit"
        color="primary"
        :disabled="saveDisabled"
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
    const saveDisabled = computed(() => !name.value || !description.value);

    if (!loggedIn()) {
      ctx.root.$router.push({ name: 'home' });
    }

    async function registerDandiset() {
      const { data } = await dandiRest.createDandiset(name.value, description.value);
      const { identifier } = data;
      ctx.root.$router.push({ name: 'dandisetLanding', params: { identifier } });
    }

    return {
      name,
      description,
      saveDisabled,
      registerDandiset,
    };
  },
});

</script>
