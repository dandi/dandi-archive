import RefParser from '@apidevtools/json-schema-ref-parser';

async function resolveSchemaReferences(schema) {
  return RefParser.dereference(schema, { dereference: { circular: false } });
}

// eslint-disable-next-line import/prefer-default-export
export { resolveSchemaReferences };
