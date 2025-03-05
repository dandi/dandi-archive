import type { Ref } from 'vue';
import { ref, watch } from 'vue';
import { cloneDeep, isEqual } from 'lodash';
// eslint-disable-next-line import/no-cycle
import {
  setTransactionPointerLocalStorage,
  setTransactionsLocalStorage,
} from './localStorage';
// eslint-disable-next-line import/no-cycle
import type { EditorInterface } from './editor';
// eslint-disable-next-line import/no-cycle
import type { DandiModel } from './types';

interface MeditorTransaction {
  field: string,
  newValue: any,
  oldValue: any,
  complex: boolean, // true if this transaction is on the complex model, false if on basic
}

// maximum number of transactions that can be pushed
// to the stack before they start to be discarded
const MAX_TRANSACTION_STACK_SIZE = 500;

class MeditorTransactionTracker {
  private transactions: MeditorTransaction[];

  // a "pointer" to the current transaction, i.e. the index
  // of the current transaction in the transactions array
  private transactionPointer: Ref<number>;

  // true if transactions are discarded due to reaching the max stack size
  private lostTransactions: boolean;

  // a reference to the EditorInterface of the meditor
  private editorInterface: EditorInterface;

  // the current data
  public currentBasicModel: DandiModel;
  public currentComplexModel: DandiModel;

  constructor(editorInterface: EditorInterface) {
    this.currentBasicModel = cloneDeep(editorInterface.basicModel.value);
    this.currentComplexModel = cloneDeep(editorInterface.complexModel);
    this.editorInterface = editorInterface;

    this.lostTransactions = false;

    this.transactions = [];

    this.transactionPointer = ref(-1);

    // save transaction stack state to localStorage on changes
    watch(() => this.transactionPointer.value, () => {
      setTransactionsLocalStorage(
        this.editorInterface.basicModel.value.id as string,
        this.transactions,
      );
      setTransactionPointerLocalStorage(
        this.editorInterface.basicModel.value.id as string,
        this.transactionPointer.value,
      );
    });
  }

  getTransactionPointer() {
    return this.transactionPointer.value;
  }

  setTransactionPointer(value: number) {
    this.transactionPointer.value = value;
  }

  getTransactions() {
    return this.transactions;
  }

  setTransactions(transactions: MeditorTransaction[]) {
    this.transactions = transactions;
  }

  // record a new change to the metadata
  add(newModel: DandiModel, complex: boolean) {
    // if there's transactions ahead of this one (due to a previous undo), get rid of them
    if (this.transactionPointer.value < this.transactions.length - 1) {
      this.transactions.splice(
        this.transactionPointer.value + 1,
        this.transactions.length - (this.transactionPointer.value + 1),
      );
    }

    const oldModel = complex ? this.currentComplexModel : this.currentBasicModel;

    // figure out what changed and record it as a transaction
    Object.keys(oldModel).forEach((propKey) => {
      // VJSF removes empty properties from the JSON model on load, but we do not want that
      // to count as a "transaction". So if a property was *removed* (not edited), we skip it.
      if (oldModel[propKey] !== undefined && newModel[propKey] === undefined) {
        return;
      }

      if (!isEqual(oldModel[propKey], newModel[propKey])) {
        this.transactions.push({
          field: propKey,
          newValue: newModel[propKey],
          oldValue: oldModel[propKey],
          complex,
        });
        if (this.transactions.length === MAX_TRANSACTION_STACK_SIZE) {
          // If the max stack size is reached, remove an element from the bottom of the stack.
          // The transaction pointer should stay the same.
          this.transactions.shift();
          this.lostTransactions = true;
        } else {
          this.transactionPointer.value += 1;
        }
      }
    });

    if (complex) {
      this.currentComplexModel = cloneDeep(newModel);
    } else {
      this.currentBasicModel = cloneDeep(newModel);
    }
  }

  // undo a change. Returns true if the change was to a complex form, false if to a basic form.
  undo(): boolean|null {
    if (this.transactionPointer.value < 0) {
      return null;
    }

    const currentModel = this.transactions[this.transactionPointer.value].complex
      ? this.currentComplexModel : this.currentBasicModel;

    currentModel[
      this.transactions[this.transactionPointer.value].field
    ] = this.transactions[this.transactionPointer.value].oldValue;

    // make sure to apply the changes to the correct model
    if (this.transactions[this.transactionPointer.value].complex) {
      this.editorInterface.setComplexModel(currentModel);
    } else {
      this.editorInterface.setBasicModel(currentModel);
    }

    this.transactionPointer.value -= 1;

    return this.transactions[this.transactionPointer.value + 1].complex;
  }

  // redo a change. Returns true if the change was to a complex form, false if to a basic form.
  redo(): boolean|null {
    if (this.transactionPointer.value === this.transactions.length - 1) {
      return null;
    }

    this.transactionPointer.value += 1;

    const currentModel = this.transactions[this.transactionPointer.value].complex
      ? this.currentComplexModel : this.currentBasicModel;

    currentModel[
      this.transactions[this.transactionPointer.value].field
    ] = this.transactions[this.transactionPointer.value].newValue;

    // make sure to apply the changes to the correct model
    if (this.transactions[this.transactionPointer.value].complex) {
      this.editorInterface.setComplexModel(currentModel);
    } else {
      this.editorInterface.setBasicModel(currentModel);
    }

    return this.transactions[this.transactionPointer.value].complex;
  }

  areTransactionsAhead(): boolean {
    return this.transactionPointer.value < this.transactions.length - 1;
  }

  areTransactionsBehind(): boolean {
    return this.transactionPointer.value > -1;
  }

  isModified(): boolean {
    return this.transactionPointer.value > -1 || this.lostTransactions;
  }

  reset() {
    this.transactions = [];
    this.transactionPointer.value = -1;
    this.lostTransactions = false;
  }
}

export {
  MeditorTransaction,
  MeditorTransactionTracker,
};
