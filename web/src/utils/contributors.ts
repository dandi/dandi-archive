/**
 * Format a contributor's name for display.
 *
 * Person names are stored as `Last, First`; display them as `First Last`.
 * Organization names, and person names without a comma (e.g. a single name),
 * are returned unchanged.
 */
function formatContributorName(contributor: { name?: string; schemaKey?: string }): string {
  const name = contributor.name ?? '';
  if (contributor.schemaKey !== 'Person') {
    return name;
  }
  const commaIndex = name.indexOf(',');
  if (commaIndex === -1) {
    return name;
  }
  const family = name.slice(0, commaIndex).trim();
  const given = name.slice(commaIndex + 1).trim();
  return [given, family].filter(Boolean).join(' ');
}

export {
  formatContributorName,
};
