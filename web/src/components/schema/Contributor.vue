<template>
  <div>
    <v-expansion-panels>
      <template v-for="contributor in data">
        <v-expansion-panel :key="contributor.name">
          <v-expansion-panel-header>{{ contributor.name }}</v-expansion-panel-header>
          <v-expansion-panel-content>
            <object-component
              :data="contributor"
              :schema="schema"
            />
          </v-expansion-panel-content>
        </v-expansion-panel>
      </template>
    </v-expansion-panels>
  </div>
</template>

<script>
import ObjectComponent from './Object.vue';

export default {
  name: 'Contributor',
  components: {
    ObjectComponent,
  },
  props: {
    schema: {
      // The root schema of the item to render
      type: [Object],
      required: true,
    },
    data: {
      // The data at the matching level of schema
      type: [Object, Number, String, Array],
      required: true,
    },
  },
};
</script>

<style>

</style>
