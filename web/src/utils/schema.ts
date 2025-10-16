import type { JSONSchema } from "@apidevtools/json-schema-ref-parser";

/**
 * Applies various miscellaneous fixes/massages the Dandiset metadata JSON Schema
 * to make it compatible with VJSF.
 *
 * @param schema The Dandiset metadata JSON Schema
 */
export function fixSchema(schema: JSONSchema) {
  let deepCopySchema = JSON.parse(JSON.stringify(schema));

  // vjsf renders < and > as HTML tags, which breaks rendering of the schema
  // in places like help text. For example, given this description for a field:
  //
  // {
  //   ...
  //   "description": "This relation should satisfy: dandiset <relation> resource.",
  //   ...
  // }
  //
  // vjsf will render it as raw HTML, causing the < and > to be interpreted like this:
  //
  // <p>This relation should satisfy: dandiset <relation>resource</relation>.</p>
  //
  // To fix this, we escape the < and > characters that look like HTML tags.
  deepCopySchema = JSON.parse(
    JSON.stringify(deepCopySchema)
      .replace(
        /<\/?[a-zA-Z][^>\s]*[^>]*>/g, t => t.replace(/</g, '\\\\<').replace(/>/g, '\\\\>')
      )
  );

  return deepCopySchema;
}
