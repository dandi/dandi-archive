export async function getDoiMetadata(doi: string, currentUrl: string): Promise<string> {
  const prefix = currentUrl!.startsWith('https://gui-staging.dandiarchive.org/') ? 'https://handle.stage.datacite.org/' : 'https://doi.org/';
  const url = new URL(`${prefix}${doi}`);
  const headers = new Headers({
    'Accept': 'application/ld+json'
  });
  const response = await fetch(url, { headers });
  return await response.text();
}
