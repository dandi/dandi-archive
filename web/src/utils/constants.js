const dandiUrl = 'https://dandiarchive.org';
const dandiAboutUrl = 'https://dandiarchive.org/about';
const dandiDocumentationUrl = 'https://www.dandiarchive.org/handbook/10_using_dandi/';

const schemaRelease = process.env.VUE_APP_DANDISET_SCHEMA_RELEASE || '1.0.0-rc1';
const dandisetSchemaUrl = `https://raw.githubusercontent.com/dandi/schema/master/releases/${schemaRelease}/dandiset.json`;

const draftVersion = 'draft';

export {
  dandiUrl,
  dandiAboutUrl,
  dandiDocumentationUrl,
  dandisetSchemaUrl,
  draftVersion,
};
