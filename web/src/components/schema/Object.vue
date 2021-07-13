<template>
  <div>
    <template v-for="(val, key) in data">
      <template v-if="isObjectArray(val)">
        <v-row
          v-if="val || !omitEmpty"
          :key="key"
          class="mx-1"
        >
          <strong class="mr-2">{{ objectKey(key) }}:</strong>
        </v-row>
        <template v-for="item in val">
          <template v-for="(v, k) in item">
            <v-row
              v-if="k !== 'schemaKey'"
              :key="`${k}`"
              class="mx-4"
            >
              <strong class="mr-2">{{ k }}:</strong> {{ renderedValue(v) }}
            </v-row>
          </template>
          <v-divider :key="`${item}-divider`" />
        </template>
      </template>
      <template v-else>
        <v-row
          v-if="val || (!val && !omitEmpty)"
          :key="key"
          class="mx-1"
        >
          <strong class="mr-2">{{ objectKey(key) }}:</strong>{{ renderedValue(val) }}
        </v-row>
      </template>
      <br :key="key">
    </template>
  </div>
</template>

<script lang="ts">
import { computed, defineComponent, PropType } from '@vue/composition-api';
import type { JSONSchema7 } from 'json-schema';
import type { JSONSchema7WithSubSchema } from '@/utils/schema/types';
import _ from 'lodash';
import type { RenderOptions } from './types';

export default defineComponent({
  name: 'Object',
  props: {
    data: {
      // The data at the matching level of schema
      type: Object as PropType<Record<string, any>>,
      required: true,
    },
    schema: {
      // The data at the matching level of schema
      type: Object as PropType<JSONSchema7>,
      required: false,
      default: null,
    },
    options: {
      type: Object as PropType<RenderOptions>,
      required: false,
      default: () => ({} as RenderOptions),
    },
  },
  setup(props) {
    const omitEmpty = computed<boolean>(() => {
      const { options: { omitEmpty: omitEmptyProp } } = props;
      if (omitEmptyProp === undefined) { return true; }
      return omitEmptyProp;
    });

    const subschema = computed(() => {
      const { schema, data: { schemaKey } } = props;
      const schemaItems = schema.items as JSONSchema7 | undefined;

      const anyOrOneOf = (schema.anyOf || schema.oneOf) as JSONSchema7WithSubSchema[] | undefined;
      const itemsAnyOrOneOf = (
        schemaItems?.anyOf || schemaItems?.oneOf
      ) as JSONSchema7WithSubSchema[] | undefined;

      const subschemas = anyOrOneOf || itemsAnyOrOneOf;
      if (!(schemaKey && subschemas)) { return undefined; }

      return subschemas.find(
        (s: JSONSchema7WithSubSchema) => s.properties.schemaKey.const === schemaKey,
      );
    });

    function renderListOfObjects(value: any[]) {
      const newVal:any = _.map(value, (v) => v);
      return newVal;
    }

    function isObjectArray(value: unknown) {
      return Array.isArray(value) && (value[0] instanceof Object);
    }
    function renderedValue(value: unknown) {
      if (Array.isArray(value) && (value[0] instanceof Object)) {
        return renderListOfObjects(value);
      } if (Array.isArray(value)) {
        return value.join(', ');
      }

      return value;
    }

    function objectKey(itemKey: string): string {
      let selectedSchema;
      const { schema } = props;

      if (subschema.value !== undefined) {
        selectedSchema = subschema.value.properties?.[itemKey];
      } else if (schema && schema.properties) {
        selectedSchema = schema.properties[itemKey];
      }

      selectedSchema = selectedSchema as JSONSchema7 | undefined;
      return selectedSchema?.title || itemKey;
    }

    return {
      omitEmpty,
      subschema,
      renderedValue,
      objectKey,
      isObjectArray,
    };
  },
});
</script>

<style>

</style>
