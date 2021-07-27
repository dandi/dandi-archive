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

<script lang="ts">
import { computed, defineComponent, PropType } from '@vue/composition-api';
import ObjectComponent from './Object.vue';
import type { RenderOptions } from './types';

export default defineComponent({
  name: 'ObjectArray',
  components: {
    ObjectComponent,
  },
  props: {
    schema: {
      // The root schema of the item to render
      type: Object,
      required: true,
    },
    data: {
      // The data at the matching level of schema
      type: Array,
      required: true,
    },
    options: {
      type: Object as PropType<RenderOptions>,
      required: false,
      default: () => ({} as RenderOptions),
    },
  },
  setup(props) {
    const primaryKey = computed(() => props.options.primaryKey);

    function objectKey(item: Record<string, unknown>) {
      const pk = primaryKey.value;
      if (pk && pk in item) {
        return item[pk];
      }

      return Object.values(item).join('|');
    }

    return {
      primaryKey,
      objectKey,
    };
  },
});
</script>

<style>

</style>
