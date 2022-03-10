const dandiUrl = 'https://dandiarchive.org';
const dandiAboutUrl = 'https://www.dandiarchive.org/';
const dandiDocumentationUrl = 'https://www.dandiarchive.org/handbook/10_using_dandi/';
const dandiHelpUrl = 'https://github.com/dandi/helpdesk/issues/new/choose';

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

export {
  dandiUrl,
  dandiAboutUrl,
  dandiDocumentationUrl,
  draftVersion,
  dandiHelpUrl,
  VALIDATION_ICONS,
};
