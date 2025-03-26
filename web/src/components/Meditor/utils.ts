import type { JSONSchema7 } from 'json-schema';
import type { VuetifyOptions } from 'vuetify';

import { cloneDeep, pickBy } from 'lodash';
import type {
  DandiModel,
  BasicSchema,
  BasicArraySchema,
  ComplexSchema,
} from './types';
import {
  isArraySchema,
  isBasicEditorSchema,
  isComplexEditorSchema,
} from './types';

export function computeBasicSchema(schema: JSONSchema7): JSONSchema7 {
  const newProperties = pickBy(schema.properties, (val): val is BasicSchema | BasicArraySchema => (
    isBasicEditorSchema(val)
  ));
  const newRequired = schema.required?.filter(
    (key) => Object.keys(newProperties).includes(key),
  ) || [];
  const newSchema = {
    ...schema,
    properties: newProperties,
    required: newRequired,
  };

  // Title and description aren't needed and just causes rendering issues
  delete newSchema.title;
  delete newSchema.description;
  // $schema isn't needed and causes Ajv to throw an error
  delete newSchema.$schema;
  return newSchema;
}

export function computeComplexSchema(schema: JSONSchema7): JSONSchema7 {
  const newProperties = pickBy(schema.properties, (val): val is ComplexSchema => (
    isComplexEditorSchema(val)
  ));
  const newRequired = schema.required?.filter(
    (key) => Object.keys(newProperties).includes(key),
  ) || [];
  const newSchema = {
    ...schema,
    properties: newProperties,
    required: newRequired,
  };

  // Description isn't needed and just causes rendering issues
  delete newSchema.description;
  return newSchema;
}

export function populateEmptyArrays(schema: JSONSchema7, model: DandiModel) {
  // TODO: May need to create a similar function for objects

  if (schema.properties === undefined) { return; }

  const props = schema.properties;
  const arrayFields = Object.keys(props).filter(
    (key) => isArraySchema(props[key]),
  );

  arrayFields.forEach((key) => {
    if (model[key] === undefined || model[key] === null) {
      model[key] = [];
    }
  });
}

export function filterModelWithSchema(model: DandiModel, schema: JSONSchema7): DandiModel {
  const { properties } = schema;
  if (!properties) { return {}; }

  return Object.keys(model).filter(
    (key) => properties[key] !== undefined,
  ).reduce(
    (obj, key) => ({ ...obj, [key]: cloneDeep(model[key]) }),
    {},
  );
}

export function writeSubModelToMaster(
  subModel: DandiModel, subSchema: JSONSchema7, masterModel: DandiModel,
) {
  const propsToWrite = subSchema.properties;
  if (propsToWrite === undefined) { return; }

  Object.keys(propsToWrite).forEach((key) => {
    masterModel[key] = subModel[key];
  });

}

export const VJSFVuetifyDefaultProps: VuetifyOptions['defaults'] = {
  global: {
    variant: 'outlined',
    density: 'compact',
  },
};
