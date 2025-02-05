<template>
  <div>
    <v-row
      class="text-h3 font-weight-thin text-center white--text"
      no-gutters
    >
      <v-col
        class="pa-0"
        data-id="value"
      >
        {{ value }}
      </v-col>
    </v-row>
    <v-row
      class="text-h6 font-weight-light text-center secondary--text text--lighten-1"
      no-gutters
    >
      <v-col
        class="pa-0"
        data-id="name"
      >
        <a
          v-if="href"
          :href="href"
          class="secondary--text text--lighten-1"
        >
          {{ name }}</a>
        <span v-else>
          {{ name }}
        </span>
        <v-tooltip
          v-if="description"
          right
        >
          <template #activator="{ on }">
            <v-icon
              color="grey"
              size="medium"
              v-on="on"
            >
              mdi-help-circle
            </v-icon>
          </template>
          {{ description }}
        </v-tooltip>
      </v-col>
    </v-row>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

export default defineComponent({
  name: 'SingleStat',
  props: {
    value: { type: String, required: true },
    name: { type: String, required: true },
    description: { type: String, default: null, required: false },
    href: { type: String, default: null, required: false },
  },
});
</script>
