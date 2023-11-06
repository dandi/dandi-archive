import type { JSONSchema7 } from 'json-schema';

import type { ComputedRef, Ref } from 'vue';
import Vue, {
  computed, reactive, ref, watch,
} from 'vue';
import { cloneDeep } from 'lodash';

// eslint-disable-next-line import/no-cycle
import { setModelLocalStorage } from './localStorage';
import type { DandiModel, DandiModelUnion } from './types';
import {
  computeBasicSchema,
  computeComplexSchema,
  filterModelWithSchema,
  writeSubModelToMaster,
  populateEmptyArrays,
} from './utils';
// eslint-disable-next-line import/no-cycle
import { MeditorTransactionTracker } from './transactions';

/**
 * Manages the interface between the source data/schema, and the changes necessary for it to
 * operate correctly with the Meditor.
 */
class EditorInterface {
  // Not guaranteed to be up to date, use getModel()
  private model: DandiModel;

  basicModel: Ref<DandiModel>;
  complexModel: DandiModel;

  schema: JSONSchema7;
  basicSchema: JSONSchema7;
  complexSchema: JSONSchema7;

  modelValid: ComputedRef<boolean>;
  basicModelValid = ref(false);

  complexModelValid: ComputedRef<boolean>;
  complexModelValidation: Record<string, boolean> = {};

  transactionTracker: MeditorTransactionTracker

  constructor(schema: JSONSchema7, model: DandiModel) {
    this.model = cloneDeep(model);
    this.schema = cloneDeep(schema);

    populateEmptyArrays(this.schema, this.model);

    // Setup split schema
    this.basicSchema = computeBasicSchema(this.schema);
    this.complexSchema = computeComplexSchema(this.schema);

    this.basicModel = ref(filterModelWithSchema(this.model, this.basicSchema));
    this.complexModel = reactive(filterModelWithSchema(this.model, this.complexSchema));

    this.modelValid = computed(() => this.basicModelValid.value && this.complexModelValid.value);
    this.complexModelValidation = reactive(Object.keys(this.complexModel).reduce(
      (obj, key) => ({ ...obj, [key]: ref(true) }), {},
    ));

    this.complexModelValid = computed(() => Object.keys(this.complexModelValidation).every(
      (key) => !!this.complexModelValidation[key],
    ));

    this.transactionTracker = new MeditorTransactionTracker(this);

    // save model to local storage on changes
    watch(() => this.getModel(), (newModel: DandiModel) => {
      setModelLocalStorage(newModel.id as string, newModel);
    });
  }

  setModel(model: DandiModel) {
    this.setBasicModel(filterModelWithSchema(model, this.basicSchema));
    this.setComplexModel(filterModelWithSchema(model, this.complexSchema));
  }

  syncModel() {
    writeSubModelToMaster(this.basicModel.value, this.basicSchema, this.model);
    writeSubModelToMaster(this.complexModel, this.complexSchema, this.model);
  }

  getModel(): DandiModel {
    this.syncModel();
    return this.model;
  }

  setBasicModel(newModel: DandiModel) {
    Object.entries(newModel).forEach(([key, value]) => {
      Vue.set(this.basicModel.value, key, value);
    });
  }

  setComplexModel(newModel: DandiModel) {
    Object.entries(newModel).forEach(([key, value]) => {
      Vue.set(this.complexModel, key, value);
    });
  }

  setComplexModelProp(propKey: string, value: DandiModelUnion) {
    Vue.set(this.complexModel, propKey, value);
  }
}

export {
  EditorInterface,
};
