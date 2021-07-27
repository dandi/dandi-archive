export interface User {
  username: string,
  name: string,
  admin?: boolean,
}

export interface Dandiset {
  identifier: string,
  created: string,
  modified: string,
  // eslint-disable-next-line no-use-before-define
  draft_version?: Version,
  // eslint-disable-next-line no-use-before-define
  most_recent_published_version?: Version,
  contact_person?: string,
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
