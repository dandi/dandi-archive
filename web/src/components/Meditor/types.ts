import type { JSONSchema7, JSONSchema7Definition, JSONSchema7TypeName } from 'json-schema';

export type DandiModel = Record<string, unknown>
export type DandiModelUnion = DandiModel | DandiModel[];

export type TransformFunction = (model: DandiModel) => unknown;
export type TransformTable = Map<string, TransformFunction>;

export type JSONSchemaUnionType = JSONSchema7Definition | JSONSchema7Definition[];
export type JSONSchemaTypeNameUnion = JSONSchema7TypeName | JSONSchema7TypeName[] | undefined;
export type BasicTypeName = 'number' | 'integer' | 'string' | 'boolean' | 'null';

export interface BasicSchema extends JSONSchema7 {
  type: BasicTypeName;

  // There's likely more fields we can narrow to undefined
  items: undefined;
}

export interface ObjectSchema extends JSONSchema7 {
  type: 'object'
  properties: {
    [key: string]: JSONSchema7Definition;
  };
}

export interface ArraySchema extends JSONSchema7 {
  type: 'array'
  items: JSONSchemaUnionType;
}

export interface ComplexSchema extends JSONSchema7 {
  type: 'object' | 'array'
}

export interface BasicArraySchema extends JSONSchema7 {
  type: 'array';
  items: BasicSchema
}

type SchemaKeyPropertiesIntersection = {
  [key: string]: JSONSchema7Definition;
} & {
  schemaKey: {
    type: 'string';
    const: string;
  };
};

export interface JSONSchema7WithSubSchema extends JSONSchema7 {
  properties: SchemaKeyPropertiesIntersection;
}

export const basicTypes = ['number', 'integer', 'string', 'boolean', 'null'];
export const isBasicType = (type: JSONSchemaTypeNameUnion): type is BasicTypeName => (
  type !== undefined
  && !Array.isArray(type)
  && basicTypes.includes(type)
);

export const isJSONSchema = (schema: JSONSchemaUnionType): schema is JSONSchema7 => (
  typeof schema !== 'boolean'
  && !Array.isArray(schema)
);

export const isBasicSchema = (schema: JSONSchemaUnionType): schema is BasicSchema => (
  isJSONSchema(schema)
  && (isBasicType(schema.type))
);

export const isObjectSchema = (schema: JSONSchemaUnionType): schema is ObjectSchema => (
  isJSONSchema(schema) && schema.properties !== undefined && schema.type === 'object'
);

export const isArraySchema = (schema: JSONSchemaUnionType): schema is BasicArraySchema => (
  isJSONSchema(schema)
  && schema.items !== undefined
  && schema.type === 'array'
);

export const isBasicArraySchema = (schema: JSONSchemaUnionType): schema is BasicArraySchema => (
  isArraySchema(schema) && isBasicSchema(schema.items)
);

export const isEnum = (schema: JSONSchemaUnionType): boolean => (
  isBasicSchema(schema) && schema.enum !== undefined
);

export const isArrayEnum = (schema: JSONSchemaUnionType): boolean => (
  isArraySchema(schema) && schema.items.enum !== undefined
);

export const isRecord = (obj: unknown): obj is Record<string, unknown> => (
  typeof obj === 'object' && obj !== null && !Array.isArray(obj)
);

export const isDandiModel = (given: unknown): given is DandiModel => (
  isRecord(given)
);

export const isDandiModelArray = (given: unknown): given is DandiModel[] => (
  Array.isArray(given) && given.every((entry) => isDandiModel(entry))
);

export const isDandiModelUnion = (given: unknown): given is DandiModelUnion => (
  isDandiModel(given) || isDandiModelArray(given)
);

export const isBasicEditorSchema = (schema: JSONSchemaUnionType): boolean => (
  isBasicSchema(schema) || isBasicArraySchema(schema) || isArrayEnum(schema)
);

export const isComplexEditorSchema = (schema: JSONSchemaUnionType): boolean => (
  !isBasicEditorSchema(schema)
);
