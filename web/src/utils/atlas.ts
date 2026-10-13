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
