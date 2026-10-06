/**
 * The file browser's side of the table viewer.
 *
 * The viewer is driven entirely by a query parameter, so that opening a table
 * is an ordinary navigation: the link can be shared, it comes back with the
 * viewer open, and the back button closes it. This module holds the little that
 * the file browser itself needs to know about that; everything else lives in
 * TableViewer.vue, which reads the same parameter.
 */

import type { RouteLocationNormalizedLoaded, RouteLocationRaw } from 'vue-router';

import type { AssetPath } from '@/types';
import { isTabularFile } from '@/utils/tabular';

/** Query parameter holding the path of the asset open in the table viewer. */
export const TABLE_QUERY_PARAM = 'table';

export function firstQueryValue(value: unknown): string | undefined {
  if (Array.isArray(value)) {
    return value[0] ?? undefined;
  }
  return typeof value === 'string' ? value : undefined;
}

/** Whether an item is an asset the table viewer can display. */
export function viewableAsTable(item: AssetPath): boolean {
  return !!item.asset && isTabularFile(item.path);
}

/**
 * The route that opens an item in the table viewer, or undefined for items the
 * viewer can't display, which are left to open however they otherwise would.
 */
export function tableViewerRoute(
  item: AssetPath,
  route: RouteLocationNormalizedLoaded,
): RouteLocationRaw | undefined {
  if (!viewableAsTable(item)) {
    return undefined;
  }
  return {
    name: 'fileBrowser',
    query: { ...route.query, [TABLE_QUERY_PARAM]: item.path },
  } as RouteLocationRaw;
}
