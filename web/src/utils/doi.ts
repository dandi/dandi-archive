import axios from 'axios';

export async function getDoiMetadata(doi: string, currentUrl: string): Promise<string> {
  const prefix = currentUrl!.startsWith('https://gui-staging.dandiarchive.org/')
    ? 'https://handle.stage.datacite.org/'
    : 'https://doi.org/';
  const url = `${prefix}${doi}`;

  const response = await axios.get(url, {
    headers: {
      'Accept': 'application/ld+json',
    },
  });
  return response.data;
}
