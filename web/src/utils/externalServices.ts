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
  },

  {
    name: "QuiltData",
    regex: /\.zarr$/,
    maxsize: Infinity,
    endpoint: (item: ServiceUrlData) => {
      if (!item.zarr_id) {
        return null;
      }
      // Extract bucket name from S3 URL
      // Handles formats like:
      // - https://s3.amazonaws.com/bucket/zarr/...
      // - https://bucket.s3.amazonaws.com/zarr/...
      const bucketMatch = item.assetS3Url.match(/(?:https?:\/\/s3[^/]*\.amazonaws\.com\/([^/]+)|https?:\/\/([^.]+)\.s3[^/]*\.amazonaws\.com)/);
      const bucket = bucketMatch ? (bucketMatch[1] || bucketMatch[2]) : 'dandiarchive';
      return `https://open.quiltdata.com/b/${bucket}/tree/zarr/${item.zarr_id}/`;
    },
  }
];

/**
 * Extract zarr_id from contentUrl for zarr files.
 * The zarr_id is the UUID that appears after '/zarr/' in the S3 URL path.
 * Example: https://s3.amazonaws.com/dandiarchive/zarr/7b617177-ad57-4f7f-806b-060e18f42d15/
 * Returns: 7b617177-ad57-4f7f-806b-060e18f42d15
 */
function extractZarrId(contentUrl: string): string | null {
  const zarrMatch = contentUrl.match(/\/zarr\/([a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})/);
  return zarrMatch ? zarrMatch[1] : null;
}

interface ServiceUrlData {
  dandisetId: string,
  dandisetVersion: string,
  assetId: string,
  assetUrl: string,
  assetDandiUrl: string,
  assetDandiMetadataUrl: string,
  assetS3Url: string,
  // zarr_id is extracted from contentUrl for zarr files
  // See: https://github.com/dandi/dandi-schema/issues/356 for potential future improvements
  zarr_id: string | null,
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
    .replaceAll('$asset_s3_url$', data.assetS3Url)
    .replaceAll('$zarr_id$', data.zarr_id || '');
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
  const assetDandiMetadataUrl = `${baseApiUrl}assets/${path.asset?.asset_id}/`;
  const assetDandiUrl = `${assetDandiMetadataUrl}download/`;
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

  // Extract zarr_id from contentUrl for zarr files
  const zarr_id = extractZarrId(assetS3Url);

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
        zarr_id,
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
