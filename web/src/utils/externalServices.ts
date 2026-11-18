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

// Constants for zarr ID and S3 URL parsing
const UUID_REGEX_PATTERN = /[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}/;
// Require the id to be a full path component, so e.g. `/zarr/<uuid>-copy` does not yield a truncated id
const ZARR_ID_REGEX = new RegExp(`/zarr/(${UUID_REGEX_PATTERN.source})(?:/|$)`);
// Hostname of an AWS S3 endpoint, optionally prefixed by a bucket name (virtual-hosted-style), e.g.
// s3.amazonaws.com, s3.us-east-2.amazonaws.com, s3-us-west-2.amazonaws.com, <bucket>.s3.amazonaws.com
const S3_HOSTNAME_REGEX = /^(?:(.+)\.)?s3(?:[.-][a-z0-9-]+)?\.amazonaws\.com$/;

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
    regex: /\.nii(\.gz)?$/,
    maxsize: Infinity,
    endpoint:
      "https://neurosift.app/dandiset/$dandiset_id$?tab=$asset_path$",
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
    name: "QuiltData: S3 Browser",
    regex: /\.zarr$/,
    maxsize: Infinity,
    endpoint: (item: ServiceUrlData) => {
      // Objects of embargoed (or still unembargoing) dandisets are not publicly readable,
      // so do not offer a public S3 browser for them. Fail closed while the dandiset
      // metadata is not loaded yet.
      const store = useDandisetStore();
      if (store.dandiset?.dandiset.embargo_status !== 'OPEN') {
        return null;
      }
      if (!item.zarr_id) {
        return null;
      }
      const bucket = extractS3Bucket(item.assetS3Url);
      if (!bucket) {
        // Not an AWS S3 URL we understand (e.g. MinIO in local development)
        return null;
      }
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
  const zarrMatch = contentUrl.match(ZARR_ID_REGEX);
  return zarrMatch ? zarrMatch[1] : null;
}

/**
 * Extract the bucket name from an AWS S3 URL, or return null if it cannot be determined
 * (e.g. MinIO in local development, or any other non-AWS endpoint).
 * Handles both virtual-hosted-style and path-style S3 URLs:
 * - Virtual-hosted-style: https://bucket.s3.amazonaws.com/... (what dandi-archive emits)
 * - Path-style: https://s3.amazonaws.com/bucket/...
 */
function extractS3Bucket(s3Url: string): string | null {
  let url: URL;
  try {
    url = new URL(s3Url);
  } catch {
    return null;
  }

  const hostnameMatch = url.hostname.match(S3_HOSTNAME_REGEX);
  if (!hostnameMatch) {
    return null;
  }

  // Virtual-hosted-style: the bucket is the hostname prefix (bucket names may contain dots)
  if (hostnameMatch[1]) {
    return hostnameMatch[1];
  }

  // Path-style: the bucket is the first path component
  return url.pathname.split('/')[1] || null;
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
  assetPath: string,
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
    .replaceAll('$asset_path$', data.assetPath);
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
  const assetPath = path.path;

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
        assetPath,
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
