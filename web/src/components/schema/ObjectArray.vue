<template>
  <div>
    <v-expansion-panels>
      <v-expansion-panel
        v-for="item in data"
        :key="objectKey(item)"
      >
        <v-expansion-panel-header>{{ item[primaryKey] }}</v-expansion-panel-header>
        <v-expansion-panel-content>
          <object-component
            :data="item"
            :schema="schema.items"
          />
        </v-expansion-panel-content>
      </v-expansion-panel>
    </v-expansion-panels>
  </div>
</template>

<script>
import ObjectComponent from './Object.vue';

export default {
  name: 'ObjectArray',
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
      type: Array,
      required: true,
    },
    options: {
      type: Object,
      required: false,
      default: () => ({}),
    },
  },
  computed: {
    primaryKey() {
      return this.options.primaryKey;
    },
  },
  methods: {
    objectKey(item) {
      if (this.primaryKey) { return item[this.primaryKey]; }

      return Object.values(item).join('|');
    },
  },
};
</script>

<style>

</style>
