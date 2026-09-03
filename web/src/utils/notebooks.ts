import axios from 'axios';

export interface ExampleNotebook {
  path: string;
  github_url: string;
  colab_url: string | null;
  docker_image: string | null;
  docker_command: string | null;
}

interface NotebooksIndexEntry {
  index_url: string;
  notebooks: ExampleNotebook[];
}

interface NotebooksIndex {
  schema_version: number;
  index_url: string;
  docker_help_url: string;
  dandisets: Record<string, NotebooksIndexEntry>;
}

export interface DandisetNotebooks {
  siteUrl: string;
  dockerHelpUrl: string;
  notebooks: ExampleNotebook[];
}

const NOTEBOOKS_INDEX_URL = 'https://notebooks.dandiarchive.org/notebooks.json';

let indexPromise: Promise<NotebooksIndex | null> | null = null;

function loadIndex(): Promise<NotebooksIndex | null> {
  if (!indexPromise) {
    indexPromise = axios.get<NotebooksIndex>(NOTEBOOKS_INDEX_URL)
      .then((response) => response.data)
      .catch((error) => {
        console.error('Error fetching the example notebooks index:', error);
        return null;
      });
  }
  return indexPromise;
}

const cache = new Map<string, DandisetNotebooks | null>();

export async function getExampleNotebooks(identifier: string): Promise<DandisetNotebooks | null> {
  if (cache.has(identifier)) {
    return cache.get(identifier)!;
  }
  const index = await loadIndex();
  const entry = index?.dandisets[identifier];
  let result: DandisetNotebooks | null = null;
  if (index && entry && entry.notebooks.length > 0) {
    result = {
      siteUrl: entry.index_url,
      dockerHelpUrl: index.docker_help_url,
      notebooks: [...entry.notebooks],
    };
  }
  cache.set(identifier, result);
  return result;
}
