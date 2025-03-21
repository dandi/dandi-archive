import axios from 'axios';

export async function getDoiMetadata(doi: string): Promise<string> {
  const prefix = import.meta.env.VITE_APP_DOI_SERVER;
  const url = `${prefix}${doi}`;

  try {
    const response = await axios.get(url, {
      headers: {
        'Accept': 'application/ld+json',
      },
    });
    return JSON.stringify(response.data);
  } catch (error) {
    // A failure to retrieve the DOI metadata should not crash the app,
    // so fail safe with an empty string.
    console.error('Error fetching DOI metadata:', error);
    return '';
  }
}
