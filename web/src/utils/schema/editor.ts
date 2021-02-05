import type { JSONSchema7 } from 'json-schema';

import Vue from 'vue';
import {
  computed, reactive, ref, ComputedRef,
} from '@vue/composition-api';
import { cloneDeep } from 'lodash';

import { DandiModel } from './types';
import {
  computeBasicSchema,
  computeComplexSchema,
  filterModelWithSchema,
  writeSubModelToMaster,
} from './utils';

import { SchemaHandler } from './handler';

/**
 * Manages the interface between the source data/schema, and the changes necessary for it to
 * operate correctly with the Meditor.
 */
class EditorInterface {
  // Not guaranteed to be up to date, use getModel()
  private model: DandiModel;

  basicModel: DandiModel;
  complexModel: DandiModel;

  schema: JSONSchema7;
  basicSchema: JSONSchema7;
  complexSchema: JSONSchema7;

  modelValid: ComputedRef<boolean>;
  basicModelValid = ref(false);

  complexModelValid: ComputedRef<boolean>;
  complexModelValidation: Record<string, boolean> = {};

  constructor(handler: SchemaHandler) {
    if (handler.model === undefined) {
      throw new Error('Cannot instantiate EditorInterface with undefined model.');
    }

    this.model = cloneDeep(handler.model);
    this.schema = cloneDeep(handler.schema);

    // Setup split schema
    this.basicSchema = computeBasicSchema(this.schema);
    this.complexSchema = computeComplexSchema(this.schema);

    this.basicModel = reactive(filterModelWithSchema(this.model, this.basicSchema));
    this.complexModel = reactive(filterModelWithSchema(this.model, this.complexSchema));

    this.modelValid = computed(() => this.basicModelValid.value && this.complexModelValid.value);
    this.complexModelValidation = reactive(Object.keys(this.complexModel).reduce(
      (obj, key) => ({ ...obj, [key]: ref(true) }), {},
    ));

    this.complexModelValid = computed(() => Object.keys(this.complexModelValidation).every(
      (key) => !!this.complexModelValidation[key],
    ));
  }

  syncModel() {
    writeSubModelToMaster(this.basicModel, this.basicSchema, this.model);
    writeSubModelToMaster(this.complexModel, this.complexSchema, this.model);
  }

  getModel(): DandiModel {
    this.syncModel();
    return this.model;
  }

  setComplexModelProp(propKey: string, value: DandiModel) {
    Vue.set(this.complexModel, propKey, value);
  }
}

export {
  // eslint-disable-next-line import/prefer-default-export
  EditorInterface,
};
