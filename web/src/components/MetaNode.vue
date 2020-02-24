<template>
<div>
  <template v-if="leaf">
    <v-text-field
      :label="schema.title"
      :type="fieldType(schema)"
      v-model="value"
      @input="bubbleInput"
      :class="`ml-${level*2}`"
      dense
    />
  </template>
  <template v-else-if="array">
    <template v-for="(el, i) in value">
      <meta-node
        :key="i"
        :schema="schema.items"
        :initial="el"
        :level="level+1"
        v-model="value[i]"
        @input="bubbleInput"
      />
    </template>
    <v-btn
      color="primary"
      dark
      rounded
      :class="`ml-${level*2}`"
      @click="addArrayItem"
    >
      <v-icon left>mdi-plus</v-icon>
      Add Item
    </v-btn>
  </template>
  <template v-else v-for="(prop, k) in totalProperties">
    <v-card :key="k" class="mb-2" flat>
      <v-card-title v-if="!isLeaf(prop)">{{prop.title}}</v-card-title>
      <meta-node
        :schema="prop"
        :initial="value[k]"
        :level="level+1"
        v-model="value[k]"
        @input="bubbleInput"
      />
    </v-card>
  </template>
  <v-menu offset-y v-if="Object.keys(optionalProperties).length">
    <template v-slot:activator="{ on }">
      <v-btn
        color="primary"
        dark
        rounded
        v-on="on"
      >
        <v-icon left>mdi-plus</v-icon>
        Add Property
      </v-btn>
    </template>
    <v-list>
      <v-list-item
        v-for="key in Object.keys(optionalProperties)"
        :key="key"
        @click="addProperty(key)"
      >
        <v-list-item-title>{{ key }}</v-list-item-title>
      </v-list-item>
    </v-list>
  </v-menu>
</div>
</template>

<script>
export default {
  name: 'MetaNode',
  props: {
    schema: {
      type: Object,
      required: true,
    },
    initial: {
      required: false,
    },
    level: {
      type: Number,
      required: false,
      default: () => 0,
    },
  },
  data() {
    return {
      value: this.initial || this.defaultInitial(),
      additionalProps: {},
    };
  },
  computed: {
    leaf() {
      return this.isLeaf(this.schema);
    },
    array() {
      return this.schema.type === 'array';
    },
    requiredProperties() {
      if (this.leaf) {
        return {};
      }

      const props = this.schema.properties || this.schema.items.properties;
      const required = this.schema.required || this.schema.items.required;

      if (!(props && required)) {
        return {};
      }

      return Object.entries(props)
        .filter(([key]) => required.includes(key))
        .reduce((acc, [key, val]) => ({ ...acc, [key]: val }), {});
    },
    optionalProperties() {
      if (this.leaf) {
        return {};
      }

      const props = this.schema.properties || this.schema.items.properties;
      if (!props) {
        return {};
      }

      const requiredKeys = Object.keys(this.requiredProperties);
      const addedKeys = Object.keys(this.additionalProps);
      const optionalKeys = Object.keys(props)
        .filter(x => !requiredKeys.includes(x) && !addedKeys.includes(x));

      return optionalKeys.reduce((obj, key) => ({ ...obj, [key]: props[key] }), {});
    },
    totalProperties() {
      return { ...this.requiredProperties, ...this.additionalProps };
    },
  },
  methods: {
    emptyItem(type) {
      switch (type) {
        case 'object':
          return {};
        case 'array':
          return [];
        case 'string':
          return '';
        case 'number':
          return 0;
        default:
          return null;
      }
    },
    defaultInitial() {
      return this.emptyItem(this.schema.type);
    },
    isLeaf(obj) {
      return !['object', 'array'].includes(obj.type);
    },
    addArrayItem() {
      this.value.push(this.emptyItem(this.schema.items.type));
    },
    addProperty(key) {
      this.$set(this.additionalProps, key, this.optionalProperties[key]);
    },
    bubbleInput() {
      this.$emit('input', this.value);
    },
    fieldType(schema) {
      if (schema.type === 'number' || schema.type === 'integer') {
        return 'number';
      }
      return schema.type;
    },
  },
};
</script>

<style>

</style>
