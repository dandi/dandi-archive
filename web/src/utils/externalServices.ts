import { trimEnd } from "lodash";
import { computed } from "vue";

import type { AssetFile, AssetPath } from "@/types";
import { useDandisetStore } from "@/stores/dandiset";

type ExternalServiceEndpoint = string | ((item: ServiceUrlData) => string | null);

interface ExternalService {
  name: string;
  regex: RegExp;
  maxsize: number;
  endpoint: ExternalServiceEndpoint;
}

const EXTERNAL_SERVICES: ExternalService[] = [
  {
    name: "Bioimagesuite/Viewer",
    regex: /\.nii(\.gz)?$/,
    maxsize: 1e9,
    endpoint: "https://bioimagesuiteweb.github.io/unstableapp/viewer.html?image=$asset_url$",
  },

  {
    name: "MetaCell/NWBExplorer",
    regex: /\.nwb$/,
    maxsize: 1e9,
    endpoint: "http://nwbexplorer.opensourcebrain.org/nwbfile=$asset_url$",
  },

  {
    name: "VTK/ITK Viewer",
    regex: /\.ome\.zarr$/,
    maxsize: Infinity,
    endpoint: "https://kitware.github.io/itk-vtk-viewer/app/?gradientOpacity=0.3&image=$asset_url$",
  },

  {
    name: "OME Zarr validator",
    regex: /\.(ome|nii)\.zarr$/,
    maxsize: Infinity,
    endpoint: "https://ome.github.io/ome-ngff-validator/?source=$asset_url$",
  },

  {
    name: "Neurosift",
    regex: /\.nwb$/,
    maxsize: Infinity,
    endpoint:
      "https://neurosift.app/nwb?url=$asset_dandi_url$&dandisetId=$dandiset_id$&dandisetVersion=$dandiset_version$",
  },

  {
    name: "Neurosift",
    regex: /\.nwb\.lindi\.(json|tar)$/,
    maxsize: Infinity,
    endpoint:
      "https://neurosift.app/nwb?url=$asset_dandi_url$&st=lindi&dandisetId=$dandiset_id$&dandisetVersion=$dandiset_version$",
  },

  {
    name: "Neurosift",
    regex: /\.avi$/,
    maxsize: Infinity,
    endpoint:
      "https://v1.neurosift.app?p=/avi&url=$asset_dandi_url$&dandisetId=$dandiset_id$&dandisetVersion=$dandiset_version$",
  },

   {
    name: 'Neuroglancer',
    regex: /\.nii(\.gz)?$|\.zarr$/,
    maxsize: Infinity,
    endpoint: redirectNeuroglancerUrl,
  },

  {
    name: "NeuroGlass",
    regex: /\.nii(\.gz)?$|\.(ome|nii)\.zarr$/,
    maxsize: Infinity,
    endpoint:
      "https://www.neuroglass.io/new?resource=$asset_dandi_metadata_url$",
  }
];

interface ServiceUrlData {
  dandisetId: string,
  dandisetVersion: string,
  assetId: string,
  assetUrl: string,
  assetDandiUrl: string,
  assetDandiMetadataUrl: string,
  assetS3Url: string,
}

function serviceURL(endpoint: ExternalServiceEndpoint, data: ServiceUrlData): string | null {
  let resolvedEndpoint;
  if (typeof endpoint == 'string') {
    resolvedEndpoint = endpoint;
  } else if (typeof endpoint == 'function') {
    resolvedEndpoint = endpoint(data);
  } else {
    throw new Error('Invalid endpoint type');
  }

  if (!resolvedEndpoint) {
    return null;
  }

  return resolvedEndpoint
    .replaceAll('$dandiset_id$', data.dandisetId)
    .replaceAll('$dandiset_version$', data.dandisetVersion)
    .replaceAll('$asset_url$', data.assetUrl)
    .replaceAll('$asset_dandi_url$', data.assetDandiUrl)
    .replaceAll('$asset_dandi_metadata_url$', data.assetDandiMetadataUrl)
    .replaceAll('$asset_s3_url$', data.assetS3Url);
}

export function getExternalServices(path: AssetPath, info: {dandisetId: string, dandisetVersion: string}) {
  if (path.asset === null) {
    return [];
  }

  const store = useDandisetStore();
  const embargoed = computed(() => store.dandiset?.dandiset.embargo_status === 'EMBARGOED');

  const servicePredicate = (service: ExternalService, _path: AssetPath) => (
    new RegExp(service.regex).test(path.path)
          && _path.asset !== null
          && _path.aggregate_size <= service.maxsize
  );

  // Formulate the two possible asset URLs -- the direct S3 link to the relevant
  // object, and the DANDI URL that redirects to the S3 one.
  const baseApiUrl = import.meta.env.VITE_APP_DANDI_API_ROOT;
  const assetDandiUrl = `${baseApiUrl}assets/${path.asset?.asset_id}/download/`;
  const assetDandiMetadataUrl = `${baseApiUrl}assets/${path.asset?.asset_id}/`;
  const assetS3Url = trimEnd((path.asset as AssetFile).url, '/');
  const assetId = path.asset?.asset_id;

  if (!assetId) {
    // This should never happen
    throw new Error('Asset ID is not defined');
  }

  // Select the best "default" URL: the direct S3 link is better when it can be
  // used, but we're forced to supply the internal DANDI URL for embargoed
  // dandisets (since the ready-made S3 URL will prevent access in that case).
  const assetUrl = embargoed.value ? assetDandiUrl : assetS3Url;

  return EXTERNAL_SERVICES
    .filter((service) => servicePredicate(service, path))
    .flatMap((service) => {
      const url = serviceURL(service.endpoint, {
        dandisetId: info.dandisetId,
        dandisetVersion: info.dandisetVersion,
        assetId,
        assetUrl,
        assetDandiUrl,
        assetDandiMetadataUrl,
        assetS3Url,
      });
      return url ? [{ name: service.name, url }] : [];
    });
}

/**
 * Custom function used to generate the endpoint
 * for the "Neuroglancer" service
 */
function redirectNeuroglancerUrl(item: ServiceUrlData): string | null {
  const store = useDandisetStore();
  const embargoed = computed(() => store.dandiset?.dandiset.embargo_status === 'EMBARGOED');
  if (embargoed.value) {
    return null;
  }

  const assetS3Url = trimEnd(item.assetS3Url, '/');
  const baseUrl = `https://neuroglancer-demo.appspot.com/#!`; // Public neuroglancer instance
  const jsonObject = {
    layers: [
      {
        type: "image",
        source: assetS3Url,
        tab: "rendering",
        name: item.assetId,
      },
    ],
    selectedLayer: {
      visible: true,
      layer: item.assetId,
    },
    layout: "4panel",
  };

  return baseUrl + encodeURIComponent(JSON.stringify(jsonObject));
}
