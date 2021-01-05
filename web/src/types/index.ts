export interface User {
  username: string,
  first_name?: string,
  last_name?: string,
  admin?: boolean,
}

export interface Dandiset {
  identifier: string,
  created: string,
  modified: string,
}

export interface Version {
  version: string,
  name: string,
  asset_count: number,
  size: number,
  created: string,
  modified: string,
  dandiset: Dandiset,
  metadata?: object,
}

export interface Asset {
  uuid: string,
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
