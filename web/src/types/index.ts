export interface User {
  username: string,
  name: string,
  admin?: boolean,
}

export interface Dandiset {
  identifier: string,
  created: string,
  modified: string,
  // TODO these versions are girderized, they should have type Version
  draft_version?: any,
  most_recent_published_version?: any,
}

export interface Version {
  version: string,
  name: string,
  asset_count: number,
  size: number,
  status: 'Pending' | 'Validating' | 'Valid' | 'Invalid',
  validation_error?: string,
  created: string,
  modified: string,
  dandiset: Dandiset,
  metadata?: object,
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

export interface Paginated<T> {
  count: number,
  next: string,
  previous: string,
  results: T[],
}

export interface Info {
  schema_url: string;
  schema_version: string;
}
