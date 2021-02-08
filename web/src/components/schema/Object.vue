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
import type { JSONSchema7 } from 'json-schema';
import type { JSONSchema7WithSubSchema } from '@/utils/schema/types';

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
    subschema() {
      const { schemaKey } = this.data;
      const schema = this.schema as JSONSchema7;
      const schemaItems = schema.items as JSONSchema7 | undefined;

      const anyOrOneOf = (schema.anyOf || schema.oneOf) as JSONSchema7WithSubSchema[] | undefined;
      const itemsAnyOrOneOf = (
        schemaItems?.anyOf || schemaItems?.oneOf
      ) as JSONSchema7WithSubSchema[] | undefined;

      const subschemas = anyOrOneOf || itemsAnyOrOneOf;
      if (!(schemaKey && subschemas)) { return undefined; }

      return subschemas.find(
        (subschema: JSONSchema7WithSubSchema) => subschema.properties.schemaKey.const === schemaKey,
      );
    },
  },
  methods: {
    renderedValue(value: any) {
      if (Array.isArray(value)) {
        return value.join(', ');
      }

      return value;
    },
    objectKey(itemKey: string) {
      let key;
      const { schema } = this;

      if (this.subschema !== undefined) {
        key = this.subschema.properties?.[itemKey]?.title;
      } else if (schema && schema.properties) {
        key = schema.properties[itemKey]?.title;
      }

      return key || itemKey;
    },
  },
};
</script>

<style>

</style>
