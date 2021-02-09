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

<script lang="ts">
import { computed, defineComponent, PropType } from '@vue/composition-api';
import type { JSONSchema7 } from 'json-schema';
import type { JSONSchema7WithSubSchema } from '@/utils/schema/types';

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
      type: Object as PropType<Record<string, any>>,
      required: false,
      default: () => ({}),
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

    function renderedValue(value: unknown) {
      if (Array.isArray(value)) {
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
    };
  },
});
</script>

<style>

</style>
