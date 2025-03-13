import axios from 'axios';

export async function getDoiMetadata(doi: string): Promise<string> {
  const prefix = import.meta.env.VITE_APP_DOI_SERVER;
  const url = `${prefix}${doi}`;

  const response = await axios.get(url, {
    headers: {
      'Accept': 'application/ld+json',
    },
  });
  return response.data;
}
