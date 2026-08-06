import type { AxiosRequestConfig, AxiosResponse } from 'axios';
import axios from 'axios';
import { ref } from 'vue';
import OAuthClient from '@resonant/oauth-client';
import type {
  Asset,
  Dandiset,
  Paginated,
  User,
  Version,
  Info,
  AssetPath,
  Zarr,
  DandisetSearchResult,
  IncompleteUpload,
} from '@/types';
import type {
  Dandiset as DandisetMetadata,
  DandisetContributors,
  Organization,
} from '@/types/schema';
import { useDandisetStore } from '@/stores/dandiset';
import qs from 'querystring';

if (!import.meta.env.VITE_APP_DANDI_API_ROOT) {
  throw new Error('Environment variable "VITE_APP_DANDI_API_ROOT" must be set.');
}

// Ensure contains trailing slash
const dandiApiRoot = import.meta.env.VITE_APP_DANDI_API_ROOT.endsWith('/')
  ? import.meta.env.VITE_APP_DANDI_API_ROOT
  : `${import.meta.env.VITE_APP_DANDI_API_ROOT}/`;

const client = axios.create({ baseURL: dandiApiRoot });

let oauthClient: OAuthClient | null = null;
try {
  if (import.meta.env.VITE_APP_OAUTH_API_ROOT && import.meta.env.VITE_APP_OAUTH_CLIENT_ID) {
    oauthClient = new OAuthClient(
      new URL(import.meta.env.VITE_APP_OAUTH_API_ROOT),
      import.meta.env.VITE_APP_OAUTH_CLIENT_ID,
      { redirectUrl: new URL(window.location.origin) }
    );
  }
} catch {
  oauthClient = null;
}

const user = ref<User | null>(null);

const dandiRest = {
  async restoreLogin() {
    if (!oauthClient) {
      return;
    }
    await oauthClient.maybeRestoreLogin();
    if (!oauthClient.isLoggedIn) {
      return;
    }

    try {
      // Fetch user
      user.value = await this.me();
    } catch (e) {
      // A status of 401 indicates login failed, so the exception should be suppressed.
      if (axios.isAxiosError(e) && e.response?.status === 401) {
        await oauthClient.logout();
      } else {
        // Any other kind of exception indicates an error that shouldn't occur
        throw e;
      }
    }
  },
  async login() {
    if (oauthClient) {
      await oauthClient.redirectToLogin();
    }
  },
  async logout() {
    if (oauthClient) {
      await oauthClient.logout();
      user.value = null;
      localStorage.clear();
    }
  },
  async me(): Promise<User> {
    const { data: user } = await client.get('users/me/');
    user.approved = user.status === 'APPROVED';
    return user;
  },
  async newApiKey(): Promise<string> {
    const { data } = await client.post('auth/token/');
    return data;
  },
  async getApiKey(): Promise<string> {
    try {
      const { data } = await client.get('auth/token/');
      return data;
    } catch (e) {
      // If the request returned 404, the user doesn't have an API key yet
      if (axios.isAxiosError(e) && e.response?.status === 404) {
        // Create a new API key
        const data = await this.newApiKey();
        return data;
      }
      throw e;
    }
  },
  async uploads(identifier: string): Promise<IncompleteUpload[]> {
    const uploads = []
    let page = 1;

    while (true) {
      const res = await client.get(`dandisets/${identifier}/uploads/`, {params: { page }});

      uploads.push(...res.data.results);
      if (res.data.next === null) {
        break;
      }

      page += 1;
    }

    return uploads;
  },
  async clearUploads(identifier: string) {
    await client.delete(`dandisets/${identifier}/uploads/`);
  },
  async assets(
    identifier: string,
    version: string,
    config?: AxiosRequestConfig
  ): Promise<Paginated<Asset> | null> {
    try {
      const { data } = await client.get(
        `dandisets/${identifier}/versions/${version}/assets/`,
        config
      );
      return data;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response && error.response.status === 404) {
        return null;
      }
      throw error;
    }
  },
  async zarr({ dandiset }: { dandiset?: string }): Promise<Paginated<Zarr>> {
    const params: { dandiset?: string } = {};
    if (dandiset !== undefined) {
      params.dandiset = dandiset;
    }

    const resp = await client.get('zarr/', {
      params,
    });

    return resp.data;
  },
  async assetPaths(
    identifier: string,
    version: string,
    location: string,
    page: number,
    page_size: number
  ): Promise<{ count: number; results: AssetPath[] }> {
    const { data } = await client.get(`dandisets/${identifier}/versions/${version}/assets/paths/`, {
      params: {
        path_prefix: location,
        page,
        page_size,
      },
    });
    const { count, results } = data;
    return { count, results };
  },
  async versions(identifier: string, params?: any): Promise<Paginated<Version> | null> {
    try {
      const { data } = await client.get(`dandisets/${identifier}/versions/`, { params });
      return data;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response && error.response.status === 404) {
        return null;
      }
      if (axios.isAxiosError(error) && error.message === 'Network Error') {
        return null;
      }
      throw error;
    }
  },
  async specificVersion(identifier: string, version: string): Promise<Version | null> {
    try {
      const { data } = await client.get(`dandisets/${identifier}/versions/${version}/info/`);
      return data;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response && error.response.status === 404) {
        return null;
      }
      throw error;
    }
  },
  async mostRecentVersion(identifier: string) {
    // Look up the last version using page filters
    const versions = await this.versions(identifier, { page_size: 1, order: '-created' });
    if (versions === null) {
      return null;
    }
    return versions.results[0];
  },
  async dandisets(params?: any): Promise<AxiosResponse<Paginated<Dandiset>>> {
    const response = await client.get('dandisets/', { params });
    return response;
  },
  async createDandiset(
    name: string,
    metadata: Partial<DandisetMetadata>,
    config: AxiosRequestConfig = {}
  ): Promise<AxiosResponse<Dandiset>> {
    const store = useDandisetStore();
    const { schemaVersion } = store;
    return client.post(
      'dandisets/',
      { name, metadata: { name, schemaVersion, ...metadata } },
      config
    );
  },
  async createEmbargoedDandiset(
    name: string,
    metadata: Partial<DandisetMetadata>,
    embargoData: {
      hasAward: boolean;
      fundingSource?: string;
      awardNumber?: string;
      embargoEndDate?: string;
    }
  ) {
    const params: { embargo: boolean; [key: string]: any } = { embargo: true };

    // Add embargo-specific parameters
    if (embargoData.hasAward) {
      if (embargoData.fundingSource) {
        params.fundingSource = embargoData.fundingSource;
      }
      if (embargoData.awardNumber) {
        params.awardNumber = embargoData.awardNumber;
      }
    } else if (embargoData.embargoEndDate) {
      params.embargoEndDate = embargoData.embargoEndDate;
    }

    // If we have award information, add it as a contributor in the metadata
    let updatedMetadata = metadata;
    if (embargoData.hasAward && embargoData.fundingSource) {
      const award: Organization = {
        name: embargoData.fundingSource,
        schemaKey: 'Organization',
        awardNumber: embargoData.awardNumber,
        roleName: ['dcite:Funder'],
      };
      const contributor: DandisetContributors = [...(metadata.contributor || []), award];
      updatedMetadata = { ...metadata, contributor };
    }

    return this.createDandiset(name, updatedMetadata, { params });
  },
  async saveDandiset(
    identifier: string,
    version: string,
    metadata: any
  ): Promise<AxiosResponse<Version>> {
    return client.put(`dandisets/${identifier}/versions/${version}/`, {
      name: metadata.name,
      metadata,
    });
  },
  async searchDandisets(parameters: Record<string, any>): Promise<Paginated<DandisetSearchResult>> {
    const { data } = await client.get('/dandisets/search', {
      params: { ...parameters },
      paramsSerializer: (params) => qs.stringify(params),
    });
    return data;
  },
  async owners(identifier: string): Promise<AxiosResponse<User[]>> {
    return client.get(`dandisets/${identifier}/users/`);
  },
  async setOwners(identifier: string, owners: User[]) {
    return client.put(`dandisets/${identifier}/users/`, owners);
  },
  async searchUsers(username: string): Promise<User[]> {
    const { data } = await client.get('users/search/', { params: { username } });
    return data;
  },
  async publish(identifier: string, releaseNotes?: string): Promise<Version> {
    const { data } = await client.post(`dandisets/${identifier}/versions/draft/publish/`, {
      release_notes: releaseNotes,
    });
    return data;
  },
  async unembargo(identifier: string): Promise<AxiosResponse> {
    return client.post(`dandisets/${identifier}/unembargo/`);
  },
  async info(): Promise<Info> {
    const { data } = await client.get('info/');
    return data;
  },
  async stats() {
    const { data } = await client.get('stats/');
    return data;
  },
  assetManifestURI(identifier: string, version: string) {
    return `${dandiApiRoot}dandisets/${identifier}/versions/${version}/assets/`;
  },
  assetDownloadURI(identifier: string, version: string, uuid: string) {
    return `${dandiApiRoot}assets/${uuid}/download/`;
  },
  assetInlineURI(identifier: string, version: string, uuid: string) {
    return `${dandiApiRoot}assets/${uuid}/download?content_disposition=inline`;
  },
  assetMetadataURI(identifier: string, version: string, uuid: string) {
    return `${dandiApiRoot}dandisets/${identifier}/versions/${version}/assets/${uuid}`;
  },
  async deleteAsset(identifier: string, version: string, uuid: string): Promise<AxiosResponse> {
    return client.delete(
      `${dandiApiRoot}dandisets/${identifier}/versions/${version}/assets/${uuid}/`
    );
  },
  async starDandiset(identifier: string): Promise<void> {
    await client.post(`dandisets/${identifier}/star/`);
  },
  async unstarDandiset(identifier: string): Promise<void> {
    await client.delete(`dandisets/${identifier}/star/`);
  },
};

// This is done with an interceptor because the value of
// oauthClient.authHeaders is initialized asynchronously,
// and doesn't exist at all if the user isn't logged in.
// Using client.defaults.headers.common.Authorization = ...
// would not update when the headers do.
client.interceptors.request.use((config) => {
  config.headers = new axios.AxiosHeaders({
    ...(config.headers instanceof axios.AxiosHeaders ? config.headers.toJSON() : config.headers),
    ...(oauthClient?.authHeaders || {}),
  });

  return config;
});



const loggedIn = () => !!user.value;
const insideIFrame = (): boolean => window.self !== window.top;
const cookiesEnabled = (): boolean => navigator.cookieEnabled;

export {
  client,
  dandiRest,
  loggedIn,
  user,
  insideIFrame,
  cookiesEnabled,
};
