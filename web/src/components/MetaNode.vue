<template>
<div>
  <template v-for="(item, i) in requiredProperties">
    <v-card :key="i" v-if="fieldType(item) === 'object'">
      <v-card-title>{{item.title}}</v-card-title>
      <meta-node
        :item="item"
        :initial="initial[i]"
        :level="level+1"
        @input="handleInput"
      />
    </v-card>
    <v-list
      v-else-if="fieldType(item) === 'array'"
      :key="i"
      :class="`ml-${level*2}`"
    >
      <v-subheader>{{item.title}}</v-subheader>
    </v-list>
    <v-text-field
      v-else-if="fieldType(item) === 'number'"
      :key="i"
      :label="item.title"
      type="number"
      v-model.number="value[i]"
      :class="`ml-${level*2}`"
    />
    <v-text-field
      v-else
      :key="i"
      :label="item.title"
      :type="fieldType(item)"
      v-model="value[i]"
      :class="`ml-${level*2}`"
    />
  </template>
  <!-- <v-select :items="Object.keys(optionalProperties)" multiple /> -->
  <v-menu offset-y>
    <template v-slot:activator="{ on }">
      <v-btn
        color="primary"
        dark
        v-on="on"
      >
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
      type: Object,
      required: false,
      default: () => ({}),
    },
    level: {
      type: Number,
      required: false,
      default: () => 0,
    },
  },
  data() {
    return {
      value: this.initial,
      additionalKeys: [],
    };
  },
  computed: {
    requiredProperties() {
      return Object.entries(this.item.properties)
        .filter(([key]) => this.item.required.includes(key))
        .reduce((acc, [key, val]) => ({ ...acc, [key]: val }), {});
    },
    optionalProperties() {
      const requiredKeys = Object.keys(this.requiredProperties);
      const optionalKeys = Object.keys(this.item.properties).filter(x => !requiredKeys.includes(x));
      return optionalKeys.reduce((obj, key) => ({ ...obj, [key]: this.item.properties[key] }), {});
    },
  },
  methods: {
    addProperty(key) {
      this.additionalKeys.push(key);
    },
    handleInput(v) {
      this.$emit('input', v);
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
