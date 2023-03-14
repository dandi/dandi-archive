import { dandiRest } from '@/rest';
import type { DandiModel } from './types';
// eslint-disable-next-line import/no-cycle
import type { MeditorTransaction } from './transactions';

function getModelLocalStorage(identifier: string) {
  const model = localStorage.getItem(`${dandiRest.user?.username}-${identifier}-model`);
  return model ? JSON.parse(model) : null;
}

function setModelLocalStorage(identifier: string, model: DandiModel) {
  localStorage.setItem(`${dandiRest.user?.username}-${identifier}-model`, JSON.stringify(model));
}

function getTransactionsLocalStorage(identifier: string) {
  const model = localStorage.getItem(`${dandiRest.user?.username}-${identifier}-transactions`);
  return model ? JSON.parse(model) : null;
}

function setTransactionsLocalStorage(identifier: string, model: MeditorTransaction[]) {
  localStorage.setItem(`${dandiRest.user?.username}-${identifier}-transactions`, JSON.stringify(model));
}

function getTransactionPointerLocalStorage(identifier: string) {
  const model = localStorage.getItem(`${dandiRest.user?.username}-${identifier}-transactionPointer`);
  return model ? JSON.parse(model) : null;
}

function setTransactionPointerLocalStorage(identifier: string, transactionPointer: number) {
  localStorage.setItem(`${dandiRest.user?.username}-${identifier}-transactionPointer`, JSON.stringify(transactionPointer));
}

function dataInLocalStorage(identifier: string) {
  return [
    getModelLocalStorage(identifier),
    getTransactionsLocalStorage(identifier),
    getTransactionPointerLocalStorage(identifier),
  ].every((r) => r !== null);
}

function clearLocalStorage(identifier: string) {
  localStorage.removeItem(`${dandiRest.user?.username}-${identifier}-model`);
  localStorage.removeItem(`${dandiRest.user?.username}-${identifier}-transactions`);
  localStorage.removeItem(`${dandiRest.user?.username}-${identifier}-transactionPointer`);
}

export {
  getModelLocalStorage,
  setModelLocalStorage,
  getTransactionsLocalStorage,
  setTransactionsLocalStorage,
  getTransactionPointerLocalStorage,
  setTransactionPointerLocalStorage,
  dataInLocalStorage,
  clearLocalStorage,
};
