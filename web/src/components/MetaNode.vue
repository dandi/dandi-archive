<template>
<div>
  <template v-if="leaf">
    <v-text-field
      v-if="fieldType(item) === 'number'"
      :label="item.title"
      type="number"
      v-model="value"
      @input="bubbleInput"
      :class="`ml-${level*2}`"
      dense
    />
    <v-text-field
      v-else
      :label="item.title"
      :type="fieldType(item)"
      v-model="value"
      @input="bubbleInput"
      :class="`ml-${level*2}`"
      dense
    />
  </template>
  <template v-else v-for="(prop, k) in requiredProperties">
    <v-card :key="k" class="mb-2" flat>
      <v-card-title v-if="!isLeaf(prop)">{{prop.title}}</v-card-title>
      <meta-node
        v-if="prop.type === 'object'"
        :item="prop"
        :initial="value[k]"
        :level="level+1"
        v-model="value[k]"
        @input="bubbleInput"
      />
      <template v-else>
        <meta-node
          :item="prop"
          :initial="value[k]"
          :level="level+1"
          v-model="value[k]"
          @input="bubbleInput"
        />
      </template>
    </v-card>
  </template>
  <!-- <v-card :key="k" class="mb-2" flat>
    <template v-if="fieldType(item) === 'object'" v-for="(prop, k) in requiredProperties">
      <v-card-title :key="k" v-if="!isLeaf(prop)">{{prop.title}}</v-card-title>
      <meta-node
        :key="k"
        :item="prop"
        :initial="value[k]"
        :level="level+1"
        v-model="value[k]"
        @input="bubbleInput"
      />
    </template>
    <template v-else>
      <meta-node
        :item="prop"
        :initial="value[k]"
        :level="level+1"
        v-model="value[k]"
        @input="bubbleInput"
      />
    </template>
  </v-card> -->
  <!-- <v-select :items="Object.keys(optionalProperties)" multiple /> -->
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
      additionalKeys: [],
    };
  },
  computed: {
    leaf() {
      return this.isLeaf(this.item);
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
      const optionalKeys = Object.keys(props).filter(x => !requiredKeys.includes(x));
      return optionalKeys.reduce((obj, key) => ({ ...obj, [key]: props[key] }), {});
    },
  },
  methods: {
    defaultInitial() {
      if (this.item.type === 'object') return {};
      if (this.item.type === 'array') return {};
      return null;
    },
    isLeaf(obj) {
      return !['object', 'array'].includes(obj.type);
    },
    addProperty(key) {
      this.additionalKeys.push(key);
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
