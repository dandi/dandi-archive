<template>
  <component
    :is="renderComponent"
    :schema="schema"
    :data="data"
    :options="options"
  />
</template>

<script>
import Contributor from '@/components/schema/Contributor.vue';
import Primitive from '@/components/schema/Primitive.vue';
import SimpleArray from '@/components/schema/SimpleArray.vue';
import DandisetStats from '@/components/schema/DandisetStats.vue';
import ObjectArray from '@/components/schema/ObjectArray.vue';
import ObjectComponent from '@/components/schema/Object.vue';
import toggles from '@/featureToggle';

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
    renderComponent() {
      // Determines which component to render

      // Temporary for Girder
      if (!toggles.DJANGO_API) {
        switch (this.field) {
          case 'access':
            return ObjectComponent;
          case 'contributors':
          case 'publications':
          case 'associatedData':
          case 'associated_anatomy':
          case 'sponsors':
            return ObjectArray;
          default:
            break;
        }
      }

      switch (this.field) {
        case 'about':
        case 'access':
        case 'relatedResource':
        case 'variableMeasured':
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

      // Temporary for Girder
      if (!toggles.DJANGO_API) {
        switch (this.field) {
          case 'publications':
            return 'url';
          default:
            break;
        }
      }

      switch (this.field) {
        case 'access':
          return 'status';
        case 'relatedResource':
          return 'url';
        default:
          return 'name';
      }
    },
  },
};
</script>
