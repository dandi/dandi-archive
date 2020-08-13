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

<script>
import { girderRest, loggedIn } from '@/rest';

export default {
  name: 'CreateDandisetView',
  data() {
    return {
      name: '',
      description: '',
    };
  },
  computed: {
    saveDisabled() {
      return !(this.name && this.description);
    },
  },
  created() {
    if (!loggedIn()) {
      this.$router.push({ name: 'home' });
    }
  },
  methods: {
    async registerDandiset() {
      const { name, description } = this;
      const { data } = await girderRest.post('dandi', null, {
        params: {
          name,
          description,
        },
      });


      const { identifier } = data.meta.dandiset;
      this.$router.push({
        name: 'dandisetLanding',
        params: { identifier },
      });
    },
  },
};
</script>
