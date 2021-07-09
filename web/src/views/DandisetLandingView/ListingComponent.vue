<template>
  <component
    :is="renderedComponent"
    :schema="schema"
    :data="data"
    :options="options"
    :class="componentClass"
  />
</template>

<script>
import Contributor from '@/components/schema/Contributor.vue';
import Primitive from '@/components/schema/Primitive.vue';
import SimpleArray from '@/components/schema/SimpleArray.vue';
import DandisetStats from '@/components/schema/DandisetStats.vue';
import ObjectArray from '@/components/schema/ObjectArray.vue';
import ObjectComponent from '@/components/schema/Object.vue';

export default {
  name: 'ListingComponent',
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
    field: {
      // The key in the parent object
      type: String,
      required: true,
    },
  },
  computed: {
    renderedComponent() {
      // Determines which component to render

      switch (this.field) {
        case 'about':
        case 'access':
        case 'relatedResource':
        case 'variableMeasured':
        case 'wasGeneratedBy':
          return ObjectArray;
        case 'dandisetStats':
          return DandisetStats;
        case 'contributor':
          return Contributor;
        case 'keywords':
          return SimpleArray;
        default:
          break;
      }

      switch (this.schema.type) {
        case 'array':
          if (this.schema.type.items && this.schema.type.items.type === 'object') {
            return ObjectArray;
          }
          return SimpleArray;

        default:
          break;
      }

      return Primitive;
    },
    options() {
      // General purpose options for different components
      const { primaryKey } = this;
      return {
        primaryKey,
      };
    },
    primaryKey() {
      // Doesn't apply to all components

      switch (this.field) {
        case 'access':
          return 'status';
        case 'relatedResource':
          return 'url';
        default:
          return 'name';
      }
    },
    componentClass() {
      let className = '';

      switch (this.renderedComponent) {
        case ObjectComponent:
          className += 'ml-4';
          break;

        default:
          break;
      }

      return className;
    },
  },
};
</script>
