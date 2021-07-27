<template>
  <v-container
    fluid
    class="py-0 px-8"
    data-id="stat"
    :data-name="name"
  >
    <v-row class="text-h3 font-weight-thin text-center white--text">
      <v-col
        class="pa-0"
        data-id="value"
      >
        {{ value }}
      </v-col>
    </v-row>
    <v-row class="text-h6 font-weight-light text-center light-blue--text text--lighten-1">
      <v-col
        class="pa-0"
        data-id="name"
      >
        <a
          v-if="href"
          :href="href"
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
  </v-container>
</template>

<script>
export default {
  name: 'SingleStat',
  props: {
    value: { type: String, required: true },
    name: { type: String, required: true },
    description: { type: String, default: null, required: false },
    href: { type: String, default: null, required: false },
  },
};
</script>
