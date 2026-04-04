import { defineStore } from 'pinia';
import { ref } from 'vue';

/**
 * Stores the listing page context (sort, search, filters, position) so the DLP
 * can offer "page through dandisets" navigation without leaking listing params
 * into the URL.  This state is transient — it does not survive a page reload.
 */
export const useListingContextStore = defineStore('listingContext', () => {
  const pos = ref<number | null>(null);
  const sortOption = ref(0);
  const sortDir = ref(-1);
  const search = ref<string | null>(null);
  const showDrafts = ref(true);
  const showEmpty = ref(false);

  function setContext(ctx: {
    pos?: number | null;
    sortOption?: number;
    sortDir?: number;
    search?: string | null;
    showDrafts?: boolean;
    showEmpty?: boolean;
  }) {
    if (ctx.pos !== undefined) pos.value = ctx.pos;
    if (ctx.sortOption !== undefined) sortOption.value = ctx.sortOption;
    if (ctx.sortDir !== undefined) sortDir.value = ctx.sortDir;
    if (ctx.search !== undefined) search.value = ctx.search;
    if (ctx.showDrafts !== undefined) showDrafts.value = ctx.showDrafts;
    if (ctx.showEmpty !== undefined) showEmpty.value = ctx.showEmpty;
  }

  function clear() {
    pos.value = null;
    sortOption.value = 0;
    sortDir.value = -1;
    search.value = null;
    showDrafts.value = true;
    showEmpty.value = false;
  }

  return {
    pos,
    sortOption,
    sortDir,
    search,
    showDrafts,
    showEmpty,
    setContext,
    clear,
  };
});
