import {
  nextTick, onScopeDispose, ref, watch, type Ref,
} from 'vue';
import {
  useRoute, useRouter, type LocationQuery, type Router,
} from 'vue-router';

// Query updates requested in the same tick, applied together by one navigation. Applying
// them one at a time would make each start from a route that lacks the others, so only
// the last one would stick.
const pendingUpdates = new Map<string, string | undefined>();

function updateQuery(router: Router, name: string, value: string | undefined) {
  if (pendingUpdates.size === 0) {
    nextTick(() => {
      const { query, hash } = router.currentRoute.value;
      const newQuery: LocationQuery = { ...query };
      pendingUpdates.forEach((pendingValue, pendingName) => {
        if (pendingValue === undefined) {
          delete newQuery[pendingName];
        } else {
          newQuery[pendingName] = pendingValue;
        }
      });
      pendingUpdates.clear();
      router.replace({ query: newQuery, hash });
    });
  }
  pendingUpdates.set(name, value);
}

/**
 * Keep a piece of UI state (e.g. the selected tab) in a query parameter of the current URL,
 * so that reloading or sharing the URL brings back the same view.
 *
 * The returned ref follows the parameter when the URL changes, and setting it updates the
 * URL in place, without adding a browser history entry. The parameter is left out while the
 * value is `defaultValue`, and reads as `defaultValue` when missing or not in `allowed`.
 *
 * The parameter belongs to the calling component: if that component goes away while the
 * page stays the same (e.g. a tab's content when another tab is selected), the parameter
 * is removed, since what it described is no longer shown.
 */
export function useRouteQuery<T extends string>(
  name: string,
  defaultValue: T,
  allowed: readonly T[],
): Ref<T> {
  const route = useRoute();
  const router = useRouter();

  // Ignore the route change that leads to this component being unmounted.
  const routeName = route.name;
  const onSameRoute = () => route.name === routeName;

  const parse = (raw: LocationQuery[string]): T => (
    allowed.includes(raw as T) ? raw as T : defaultValue
  );

  const value = ref(parse(route.query[name])) as Ref<T>;

  watch(() => route.query[name], (raw) => {
    if (onSameRoute()) {
      value.value = parse(raw);
    }
  });

  watch(value, (newValue) => {
    if (onSameRoute() && newValue !== parse(route.query[name])) {
      updateQuery(router, name, newValue === defaultValue ? undefined : newValue);
    }
  });

  // Only when the page stays the same: the URL of a different page (e.g. another dandiset)
  // describes that page's own state.
  const routePath = route.path;
  onScopeDispose(() => {
    if (route.path === routePath && name in route.query) {
      updateQuery(router, name, undefined);
    }
  });

  return value;
}
