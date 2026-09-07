// Validation helpers shared by the optional metadata inputs on the Dandiset
// creation form. Each helper returns true when the value is acceptable and an
// error message otherwise, matching the Vuetify `rules` convention. Empty
// values are always accepted here; whether a field is required is decided by
// the input that uses the rule.

export type Rule = (v: string | undefined | null) => true | string;

// Patterns mirror the constraints in the dandischema JSON schema.
const ORCID_PATTERN = /^\d{4}-\d{4}-\d{4}-(\d{3}X|\d{4})$/;
const ROR_PATTERN = /^https:\/\/ror\.org\/[a-z0-9]+$/;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function isBlank(v: string | undefined | null): boolean {
  return !v || v.trim().length === 0;
}

export const orcidRule: Rule = (v) => (
  isBlank(v) || ORCID_PATTERN.test(v!.trim()) || 'Enter an ORCID like 0000-0002-1825-0097'
);

export const rorRule: Rule = (v) => (
  isBlank(v) || ROR_PATTERN.test(v!.trim()) || 'Enter a ROR identifier like https://ror.org/01cwqze88'
);

export const emailRule: Rule = (v) => (
  isBlank(v) || EMAIL_PATTERN.test(v!.trim()) || 'Enter a valid email address'
);

export const urlRule: Rule = (v) => {
  if (isBlank(v)) return true;
  try {
    const url = new URL(v!.trim());
    return ['http:', 'https:'].includes(url.protocol) || 'Enter a full URL starting with https://';
  } catch {
    return 'Enter a full URL starting with https://';
  }
};

// The schema asks for "Last, First" so that citations can be generated.
export const personNameRule: Rule = (v) => (
  isBlank(v) || v!.includes(',') || 'Use the format "Last, First"'
);

export function allValid(rules: Rule[], value: string | undefined | null): boolean {
  return rules.every((rule) => rule(value) === true);
}

// Normalize an ORCID that may have been pasted as a full URL.
export function normalizeOrcid(v: string): string {
  return v.trim().replace(/^https?:\/\/orcid\.org\//, '');
}

// Convert a "First Last" display name (as reported by GitHub) into the
// "Last, First" form the schema expects. Names already containing a comma are
// returned unchanged.
export function toLastFirst(displayName: string): string {
  const name = displayName.trim();
  if (!name || name.includes(',')) return name;
  const parts = name.split(/\s+/);
  if (parts.length < 2) return name;
  const last = parts.pop();
  return `${last}, ${parts.join(' ')}`;
}
