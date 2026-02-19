import { Dandiset as DandisetMetadata } from './schema';

export { DandisetMetadata };
export * from './schema';

export interface User {
  username: string,
  name: string,
  admin?: boolean,
  email: string,
  status: 'INCOMPLETE' | 'PENDING' | 'APPROVED' | 'REJECTED',
  approved: boolean,
}

export interface Dandiset {
  identifier: string,
  created: string,
  modified: string,
  draft_version?: Version,
  most_recent_published_version?: Version,
  contact_person?: string,
  embargo_status: 'EMBARGOED' | 'UNEMBARGOING' | 'OPEN',
  star_count: number,
  is_starred: boolean,
}

export interface DandisetSearchResult extends Dandiset {
  asset_counts: Record<string, number>;
}

export interface ValidationError {
  field: string,
  message: string,
  path: string,
}

export interface Version {
  version: string,
  name: string,
  asset_count: number,
  active_uploads: number
  size: number,
  status: 'Pending' | 'Validating' | 'Valid' | 'Invalid' | 'Published',
  validation_error?: string,
  created: string,
  modified: string,
  dandiset: Dandiset,
  metadata?: DandisetMetadata,
  asset_validation_errors: ValidationError[],
  version_validation_errors: ValidationError[],
  contact_person?: string,
}

export interface Asset {
  asset_id: string,
  path: string,
  sha256: string,
  size: number,
  created: string,
  modified: string,
  version: Version,
}

export interface Zarr {
  name: string;
  dandiset: string;
  zarr_id: string;
  status: 'Pending' | 'Ingesting' | 'Complete';
  checksum: string;
  file_count: number;
  size: number;
}

export interface Paginated<T> {
  count: number,
  next: string,
  previous: string,
  results: T[],
}

export interface Info {
  instance_config: {
    instance_name: string;
    instance_identifier: string | null;
    instance_url: string | null;
    doi_prefix: string | null;
    licenses: string[];
  };
  schema_url: string;
  schema_version: string;
  'cli-minimal-version': string;
  'cli-requires-python': string;
}

export interface DandisetStats {
  asset_count: number,
  size: number,
}

export interface AssetFile {
  asset_id: string;
  url: string;
}

export interface AssetPath {
  created: string;
  modified: string;
  path: string;
  version: number;
  aggregate_files: number;
  aggregate_size: number;
  asset: AssetFile | null;
}

export interface IncompleteUpload {
  created: string;
  blob: string;
  upload_id: string;
  etag: string;
  size: number;
}
