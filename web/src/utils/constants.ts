const dandiUrl = 'https://dandiarchive.org';
const dandiAboutUrl = 'https://about.dandiarchive.org/';
const dandiDocumentationUrl = 'https://www.dandiarchive.org/handbook/10_using_dandi/';
const dandiHelpUrl = 'https://github.com/dandi/helpdesk/issues/new/choose';
const dandihubUrl = 'https://hub.dandiarchive.org/';

const draftVersion = 'draft';

const VALIDATION_ICONS = {
  // version metadata
  // https://github.com/dandi/schema/blob/master/releases/0.4.4/dandiset.json#L231
  name: 'mdi-note',
  description: 'mdi-text',
  contributor: 'mdi-account-multiple',
  license: 'mdi-gavel',
  assetsSummary: 'mdi-file-multiple',

  // asset metadata
  // https://github.com/dandi/schema/blob/master/releases/0.4.4/asset.json#L312
  contentSize: 'mdi-table-of-contents',
  encodingFormat: 'mdi-code-json',
  digest: 'mdi-barcode',
  path: 'mdi-folder-multiple',
  identifier: 'mdi-identifier',

  // icon to use when one isn't found
  DEFAULT: 'mdi-alert',
};

const sortingOptions = [
  {
    name: 'Modified',
    djangoField: 'modified',
  },
  {
    name: 'Identifier',
    djangoField: 'id',
  },
  {
    name: 'Name',
    djangoField: 'name',
  },
  {
    name: 'Size',
    djangoField: 'size',
  },
];

const DANDISETS_PER_PAGE = 8;

export {
  dandiUrl,
  dandiAboutUrl,
  dandiDocumentationUrl,
  dandihubUrl,
  draftVersion,
  dandiHelpUrl,
  VALIDATION_ICONS,
  sortingOptions,
  DANDISETS_PER_PAGE,
};
