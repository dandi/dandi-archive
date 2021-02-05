<template>
  <div>
    <template v-for="(val, key) in data">
      <v-row
        v-if="val || (!val && !omitEmpty)"
        :key="key"
      >
        <strong class="mr-2">{{ objectKey(key) }}:</strong> {{ renderedValue(val) }}
      </v-row>
    </template>
  </div>
</template>

<script>
export default {
  name: 'Object',
  props: {
    data: {
      // The data at the matching level of schema
      type: Object,
      required: true,
    },
    schema: {
      // The data at the matching level of schema
      type: Object,
      required: false,
      default: null,
    },
    options: {
      type: Object,
      required: false,
      default: () => ({}),
    },
  },
  computed: {
    omitEmpty() {
      return this.options.omitEmpty || true;
    },
  },
  methods: {
    renderedValue(value) {
      if (Array.isArray(value)) {
        return value.join(', ');
      }

      return value;
    },
    objectKey(itemKey) {
      const { schema } = this;

      if (schema && schema.properties && itemKey in schema.properties) {
        return schema.properties[itemKey].title;
      }
      return itemKey;
    },
  },
};
</script>

<style>

</style>
