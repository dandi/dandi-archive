// Builds the Python code shown on the dandiset landing page's Python tab.

const DEFAULT_API_ROOT = 'https://api.dandiarchive.org/api';

export interface PythonSnippetOptions {
  identifier: string;
  version: string;
  // The DANDI API root the page talks to. The client argument is omitted for the
  // main archive, which is the DandiAPIClient default.
  apiRoot: string;
  embargoed: boolean;
  // Path of an NWB file in the dandiset, or null if it has none.
  nwbPath: string | null;
  // Path of any asset in the dandiset, used when there is no NWB file.
  anyPath: string | null;
}

function pyString(value: string): string {
  return JSON.stringify(value);
}

function clientLines(apiRoot: string, embargoed: boolean): string[] {
  const root = apiRoot.replace(/\/+$/, '');
  const lines = [
    root === DEFAULT_API_ROOT
      ? 'client = DandiAPIClient()'
      : `client = DandiAPIClient(api_url=${pyString(root)})`,
  ];
  if (embargoed) {
    lines.push(
      '# This dandiset is embargoed. Set the DANDI_API_KEY environment variable to',
      '# the API key of an account that owns it before running this.',
      'client.dandi_authenticate()',
    );
  }
  return lines;
}

export function pythonSnippet(options: PythonSnippetOptions): string {
  const {
    identifier, version, apiRoot, embargoed, nwbPath, anyPath,
  } = options;
  const header = [
    'from itertools import islice',
    '',
    'from dandi.dandiapi import DandiAPIClient',
  ];
  const setup = [
    ...clientLines(apiRoot, embargoed),
    `dandiset = client.get_dandiset(${pyString(identifier)}, ${pyString(version)})`,
    '',
  ];

  if (nwbPath) {
    // Embargoed content is served through signed URLs, so the query string has
    // to stay on the URL for the request to be authorized.
    const stripQuery = embargoed ? '' : ', strip_query=True';
    return [
      '# pip install dandi pynwb remfile',
      ...header,
      'import h5py',
      'import pynwb',
      'import remfile',
      '',
      ...setup,
      '# List the first few NWB files in this dandiset.',
      'for asset in islice(dandiset.get_assets_by_glob("*.nwb"), 10):',
      '    print(asset.path)',
      '',
      '# Stream one of them. Change this path to open a different file.',
      `asset = dandiset.get_asset_by_path(${pyString(nwbPath)})`,
      `url = asset.get_content_url(follow_redirects=1${stripQuery})`,
      '',
      'h5_file = h5py.File(remfile.File(url), "r")',
      'io = pynwb.NWBHDF5IO(file=h5_file)',
      'nwbfile = io.read()',
      'print(nwbfile)',
      '',
    ].join('\n');
  }

  const lines = [
    '# pip install dandi',
    ...header,
    '',
    ...setup,
    '# List the first few files in this dandiset.',
    'for asset in islice(dandiset.get_assets(), 10):',
    '    print(asset.path)',
  ];
  // Zarr assets are directories and cannot be fetched with asset.download().
  if (anyPath && !/\.zarr$/i.test(anyPath)) {
    lines.push(
      '',
      '# Download one of them. Change this path to fetch a different file.',
      `asset = dandiset.get_asset_by_path(${pyString(anyPath)})`,
      'asset.download(asset.path.split("/")[-1])',
    );
  }
  lines.push('');
  return lines.join('\n');
}
