import axios from 'axios';

const ATLAS_URL = 'https://atlas.dandiarchive.org';
const ATLAS_INDEX_URL = `${ATLAS_URL}/data/atlases_index.json`;

export interface Atlas {
  key: string;
  name: string;
}

interface AtlasIndexEntry extends Atlas {
  dandisets?: string[];
}

let atlasByDandiset: Promise<Map<string, Atlas>> | undefined;

async function fetchAtlasIndex(): Promise<Map<string, Atlas>> {
  const response = await axios.get<{ atlases?: AtlasIndexEntry[] }>(ATLAS_INDEX_URL);
  const index = new Map<string, Atlas>();
  response.data.atlases?.forEach(({ key, name, dandisets }) => {
    dandisets?.forEach((identifier) => {
      // A Dandiset can be registered against more than one atlas. Any of them is a
      // reasonable destination, so the first one in the index wins.
      if (!index.has(identifier)) {
        index.set(identifier, { key, name });
      }
    });
  });
  return index;
}

/**
 * Return the atlas that the DANDI Atlas viewer can display this Dandiset in, or
 * `undefined` if there is none. Only meaningful for Dandiset identifiers on the
 * production instance, since that is the only one the viewer indexes.
 */
export async function getAtlasForDandiset(identifier: string): Promise<Atlas | undefined> {
  if (atlasByDandiset === undefined) {
    atlasByDandiset = fetchAtlasIndex();
  }

  try {
    return (await atlasByDandiset).get(identifier);
  } catch (error) {
    // The rest of the page works without this link, so fail safe by omitting it.
    // Clearing the cache lets a later navigation retry the request.
    console.error('Error fetching the DANDI Atlas index:', error);
    atlasByDandiset = undefined;
    return undefined;
  }
}

export function atlasDandisetURL(atlasKey: string, identifier: string): string {
  return `${ATLAS_URL}/?atlas=${atlasKey}#dandiset=${identifier}`;
}

/**
 * The subjects and sessions of one Dandiset that the DANDI Atlas viewer can show.
 * `sessions` maps each indexed asset ID to its subject.
 */
export interface AtlasLookup {
  subjects: Set<string>;
  sessions: Map<string, string>;
}

const atlasLookups = new Map<string, Promise<AtlasLookup | undefined>>();

async function fetchAtlasLookup(atlasKey: string, identifier: string): Promise<AtlasLookup | undefined> {
  const url = `${ATLAS_URL}/data/atlases/${atlasKey}/dandisets/${identifier}.json`;
  try {
    const { data } = await axios.get<{ subjects?: string[]; sessions?: Record<string, string> }>(url);
    return {
      subjects: new Set(data.subjects ?? []),
      sessions: new Map(Object.entries(data.sessions ?? {})),
    };
  } catch (error) {
    // The file browser works without these links, so fail safe by omitting them.
    console.error('Error fetching the DANDI Atlas subjects and sessions:', error);
    return undefined;
  }
}

/**
 * Return the subjects and sessions of this Dandiset that the given atlas indexes, or
 * `undefined` if the viewer publishes none. Fetched once per Dandiset and atlas.
 */
export function getAtlasLookup(atlasKey: string, identifier: string): Promise<AtlasLookup | undefined> {
  const key = `${atlasKey}/${identifier}`;
  let lookup = atlasLookups.get(key);
  if (lookup === undefined) {
    lookup = fetchAtlasLookup(atlasKey, identifier);
    atlasLookups.set(key, lookup);
  }
  return lookup;
}

export function atlasSubjectURL(atlasKey: string, identifier: string, subject: string): string {
  return `${atlasDandisetURL(atlasKey, identifier)}&subject=${encodeURIComponent(subject)}`;
}

export function atlasSessionURL(
  atlasKey: string,
  identifier: string,
  subject: string,
  assetId: string,
): string {
  return `${atlasSubjectURL(atlasKey, identifier, subject)}&session=${encodeURIComponent(assetId)}`;
}
