<template>
<div>
  <template v-if="leaf">
    <v-text-field
      :label="item.title"
      :type="fieldType(item)"
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
        :item="item.items"
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
        :item="prop"
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
    item: {
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
      return this.isLeaf(this.item);
    },
    array() {
      return this.item.type === 'array';
    },
    requiredProperties() {
      if (this.leaf) {
        return {};
      }

      const props = this.item.properties || this.item.items.properties;
      const required = this.item.required || this.item.items.required;

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
      const props = this.item.properties || this.item.items.properties;
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
      return this.emptyItem(this.item.type);
    },
    isLeaf(obj) {
      return !['object', 'array'].includes(obj.type);
    },
    addArrayItem() {
      this.value.push(this.emptyItem(this.item.items.type));
    },
    addProperty(key) {
      this.$set(this.additionalProps, key, this.optionalProperties[key]);
    },
    bubbleInput() {
      this.$emit('input', this.value);
    },
    fieldType(item) {
      if (item.type === 'number' || item.type === 'integer') {
        return 'number';
      }
      return item.type;
    },
  },
};
</script>

<style>

</style>
