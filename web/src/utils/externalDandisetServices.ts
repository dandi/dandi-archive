import { ref, watch } from 'vue';
import type { Ref } from 'vue';

import { useDandisetStore } from '@/stores/dandiset';
import { useInstanceStore } from '@/stores/instance';
import { atlasDandisetURL, getAtlasForDandiset } from '@/utils/atlas';

export interface DandisetServiceContext {
  dandisetId: string;
  dandisetVersion: string;
  baseApiUrl: string;
  isProduction: boolean;
  isSandbox: boolean;
}

// A function endpoint returns the link (plus any display overrides), or null to
// omit the service for this Dandiset.
interface EndpointResult {
  url: string;
  tooltip?: string;
}

type ExternalDandisetServiceEndpoint =
  | string
  | ((ctx: DandisetServiceContext) => EndpointResult | null | Promise<EndpointResult | null>);

interface ExternalDandisetService {
  name: string;
  icon: string;
  tooltip: string;
  endpoint: ExternalDandisetServiceEndpoint;
}

export interface ResolvedDandisetService {
  name: string;
  icon: string;
  tooltip: string;
  url: string;
}

const EXTERNAL_DANDISET_SERVICES: ExternalDandisetService[] = [
  {
    name: 'Neurosift',
    icon: 'mdi-web',
    tooltip: 'Open the Dandiset in Neurosift',
    // Neurosift must be told to look up sandbox Dandiset identifiers on the
    // sandbox API instead of production.
    endpoint: (ctx) => ({
      url: `https://neurosift.app/dandiset/${ctx.dandisetId}?dandisetVersion=${ctx.dandisetVersion}${ctx.isSandbox ? '&staging=1' : ''}`,
    }),
  },

  {
    name: 'AI Metadata Editor (Beta)',
    icon: 'mdi-robot',
    tooltip: 'Open the Dandiset in the AI assisted metadata editor (Beta)',
    endpoint: 'https://medit.dandiarchive.org/?dandiset=$dandiset_id$&instance=$base_api_url$',
  },

  {
    name: 'DANDI Atlas',
    icon: 'mdi-brain',
    tooltip: 'Browse the Dandiset by brain region',
    endpoint: async (ctx) => {
      // The atlas viewer only indexes Dandisets on the production instance, so
      // identifiers from any other deployment would resolve to unrelated data.
      if (!ctx.isProduction) {
        return null;
      }

      const atlas = await getAtlasForDandiset(ctx.dandisetId);
      if (!atlas) {
        return null;
      }

      return {
        url: atlasDandisetURL(atlas.key, ctx.dandisetId),
        tooltip: `Browse the Dandiset by brain region in ${atlas.name}`,
      };
    },
  },
];

async function resolveService(
  service: ExternalDandisetService,
  ctx: DandisetServiceContext,
): Promise<ResolvedDandisetService | null> {
  let result: EndpointResult | null;
  if (typeof service.endpoint === 'string') {
    result = {
      url: service.endpoint
        .replaceAll('$dandiset_id$', ctx.dandisetId)
        .replaceAll('$dandiset_version$', ctx.dandisetVersion)
        .replaceAll('$base_api_url$', ctx.baseApiUrl),
    };
  } else {
    result = await service.endpoint(ctx);
  }

  if (!result) {
    return null;
  }

  return {
    name: service.name,
    icon: service.icon,
    tooltip: result.tooltip ?? service.tooltip,
    url: result.url,
  };
}

/**
 * The external services applicable to the Dandiset currently in the store, as a
 * reactive list. Synchronous entries appear immediately; asynchronous ones (e.g.
 * the atlas index lookup) fill in when they settle, keeping registry order.
 */
export function useExternalDandisetServices(): Ref<ResolvedDandisetService[]> {
  const store = useDandisetStore();
  const instanceStore = useInstanceStore();
  instanceStore.load();

  const services = ref<ResolvedDandisetService[]>([]);

  // Bumped on every re-resolution so that async results landing after the user
  // navigates to another Dandiset (or the instance info loads) are discarded.
  let generation = 0;

  watch(
    [() => store.dandiset, () => instanceStore.isProduction, () => instanceStore.isSandbox],
    () => {
      generation += 1;
      const current = generation;

      const dandiset = store.dandiset;
      const dandisetVersion = dandiset?.metadata?.version;
      if (!dandiset || !dandisetVersion) {
        services.value = [];
        return;
      }

      const ctx: DandisetServiceContext = {
        dandisetId: dandiset.dandiset.identifier,
        dandisetVersion,
        baseApiUrl: import.meta.env.VITE_APP_DANDI_API_ROOT,
        isProduction: instanceStore.isProduction,
        isSandbox: instanceStore.isSandbox,
      };

      const slots: (ResolvedDandisetService | null)[] = EXTERNAL_DANDISET_SERVICES.map(() => null);
      services.value = [];
      EXTERNAL_DANDISET_SERVICES.forEach((service, i) => {
        resolveService(service, ctx)
          .then((resolved) => {
            if (generation !== current) {
              return;
            }
            slots[i] = resolved;
            services.value = slots.filter(
              (s): s is ResolvedDandisetService => s !== null,
            );
          })
          .catch((error) => {
            // The menu works without this entry, so fail safe by omitting it.
            console.error(`Error resolving external service "${service.name}":`, error);
          });
      });
    },
    { immediate: true },
  );

  return services;
}
