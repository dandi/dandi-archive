/**
 * Operator catalog for the dandiset list's advanced-search autocomplete.
 *
 * Mirrors the backend allowlist in
 * `dandiapi/api/services/search/operators.py` — keep in sync. The backend is
 * the source of truth (it validates and returns "Did you mean?" suggestions
 * for unknown keys); this file only powers the autocomplete UX.
 *
 * `valueExample` is shown alongside the operator name in key-mode suggestions.
 * `valueSuggestions` is an optional list of common values that the
 * autocomplete shows when the cursor is sitting past a `:` for that
 * operator. The lists are intentionally short — they're convenience hints,
 * not exhaustive controlled vocabularies (the user can still type any value).
 */

export interface SearchOperator {
  name: string;
  description: string;
  valueExample: string;
  valueSuggestions?: string[];
}

// Common values seeded from prod observation + the existing
// DandisetSearchQueryParameterSerializer choices. Not exhaustive; the user
// can still type anything.
const TECHNIQUE_VALUES = [
  'signal filtering technique',
  'spike sorting technique',
  'multi electrode extracellular electrophysiology recording technique',
  'voltage clamp technique',
  'surgical technique',
  'behavioral technique',
  'current clamp technique',
  'fourier analysis technique',
  'two-photon microscopy technique',
  'patch clamp technique',
  'analytical technique',
];

const APPROACH_VALUES = [
  'electrophysiological approach',
  'behavioral approach',
  'microscopy approach',
  'optogenetic approach',
];

const STANDARD_VALUES = [
  'Neurodata Without Borders (NWB)',
  'Brain Imaging Data Structure (BIDS)',
  'NIfTI',
];

const FILE_TYPE_VALUES = ['nwb', 'image', 'text', 'video'];

export const OPERATORS: SearchOperator[] = [
  // Date range
  { name: 'created_after', description: 'Created on or after a date', valueExample: '2024-01-01' },
  { name: 'created_before', description: 'Created before a date', valueExample: '2024-01-01' },
  { name: 'modified_after', description: 'Last modified on or after a date', valueExample: '2024-01-01' },
  { name: 'modified_before', description: 'Last modified before a date', valueExample: '2024-01-01' },
  { name: 'published_after', description: 'Most recent publication on or after', valueExample: '2024-01-01' },
  { name: 'published_before', description: 'Most recent publication before', valueExample: '2024-01-01' },
  // Asset content (these have value-suggestion lists)
  {
    name: 'species',
    description: 'Has assets attributed to a species',
    valueExample: 'mouse',
    // Species values are looked up live from /search/species — no static
    // list here; the component uses an empty array as a sentinel.
    valueSuggestions: [],
  },
  {
    name: 'approach',
    description: 'Has assets using an approach',
    valueExample: 'electrophysiology',
    valueSuggestions: APPROACH_VALUES,
  },
  {
    name: 'technique',
    description: 'Has assets using a measurement technique',
    valueExample: '"spike sorting"',
    valueSuggestions: TECHNIQUE_VALUES,
  },
  {
    name: 'standard',
    description: 'Has assets in a data standard',
    valueExample: 'nwb',
    valueSuggestions: STANDARD_VALUES,
  },
  {
    name: 'file_type',
    description: 'Has assets of a file type',
    valueExample: 'nwb',
    valueSuggestions: FILE_TYPE_VALUES,
  },
  // Permissions
  { name: 'owner', description: 'Owned by a user (name, username, or email)', valueExample: '"Jane Doe"' },
  // Contributors (catch-all + per-role)
  { name: 'contributor', description: 'Listed as a contributor (any role; matches name, email, ORCID, or ROR)', valueExample: '"Doe, Jane"' },
  { name: 'author', description: 'Listed as an Author', valueExample: 'Doe' },
  { name: 'contact_person', description: 'Listed as the Contact Person', valueExample: 'Doe' },
  { name: 'data_collector', description: 'Listed as a Data Collector', valueExample: 'Doe' },
  { name: 'data_curator', description: 'Listed as a Data Curator', valueExample: 'Doe' },
  { name: 'data_manager', description: 'Listed as a Data Manager', valueExample: 'Doe' },
  { name: 'maintainer', description: 'Listed as a Maintainer', valueExample: 'Doe' },
  { name: 'project_leader', description: 'Listed as the Project Leader', valueExample: 'Doe' },
  { name: 'funder', description: 'Listed as a Funder', valueExample: 'NIH' },
  { name: 'sponsor', description: 'Listed as a Sponsor', valueExample: 'NIH' },
  { name: 'affiliation', description: 'Has a contributor affiliated with the named organization (or ROR)', valueExample: 'Stanford' },
];

const OPERATORS_BY_NAME = new Map(OPERATORS.map((op) => [op.name, op]));

export interface TokenAtCursor {
  text: string;
  start: number;
  end: number;
}

/**
 * Inspect `text` and find the token straddling `cursor` (the index where the
 * caret sits). A "token" here is a maximal run of non-whitespace characters
 * — the same boundaries the backend parser uses to split tokens before
 * recognizing operator vs free text.
 *
 * Returns the token's text and its [start, end) range so a caller can
 * splice a replacement back in at the right place.
 */
export function tokenAtCursor(text: string, cursor: number): TokenAtCursor {
  let start = cursor;
  while (start > 0 && !/\s/.test(text[start - 1])) {
    start -= 1;
  }
  let end = cursor;
  while (end < text.length && !/\s/.test(text[end])) {
    end += 1;
  }
  return { text: text.slice(start, end), start, end };
}

/**
 * What kind of suggestions (if any) the autocomplete should show for the
 * given cursor position.
 *
 * - `key` mode: cursor is on a token without a `:` yet — suggest operator
 *   names whose name starts with the typed prefix.
 * - `value` mode: cursor is on a `key:value` token where `key` is one of
 *   the operators that has a `valueSuggestions` list — suggest values
 *   matching the typed value-prefix. The replacement range covers just
 *   the value portion (after the colon), so the user's `key:` is preserved.
 * - `none`: no suggestions (e.g. `key:` for a key with no suggestions, or
 *   the user is inside a quoted value where autocomplete would be awkward).
 */
export type SuggestMode =
  | { kind: 'key'; prefix: string; replaceStart: number; replaceEnd: number }
  | {
      kind: 'value';
      operator: SearchOperator;
      prefix: string;
      replaceStart: number;
      replaceEnd: number;
    }
  | { kind: 'none' };

export function suggestModeAt(text: string, cursor: number): SuggestMode {
  const { text: token, start, end } = tokenAtCursor(text, cursor);
  const colonIdx = token.indexOf(':');
  if (colonIdx === -1) {
    return {
      kind: 'key', prefix: token, replaceStart: start, replaceEnd: end,
    };
  }
  const key = token.slice(0, colonIdx).toLowerCase();
  const op = OPERATORS_BY_NAME.get(key);
  if (!op || op.valueSuggestions === undefined) {
    return { kind: 'none' };
  }
  const valuePrefix = token.slice(colonIdx + 1);
  // Quoted values are out of scope — the autocomplete works in
  // whitespace-bounded tokens, but quoted values can contain whitespace.
  if (valuePrefix.startsWith('"')) {
    return { kind: 'none' };
  }
  return {
    kind: 'value',
    operator: op,
    prefix: valuePrefix,
    replaceStart: start + colonIdx + 1,
    replaceEnd: end,
  };
}

/**
 * Suggestion list for key-mode (filter operators by name prefix).
 * Empty token → all operators.
 */
export function keySuggestions(prefix: string): SearchOperator[] {
  const lower = prefix.toLowerCase();
  if (lower === '') return OPERATORS;
  return OPERATORS.filter((op) => op.name.startsWith(lower));
}

/**
 * Suggestion list for value-mode (filter the operator's `valueSuggestions`
 * by case-insensitive substring on the typed prefix). Returns the raw
 * suggestion strings — callers wrap multi-word values in quotes when
 * inserting them.
 */
export function valueSuggestions(operator: SearchOperator, prefix: string): string[] {
  if (!operator.valueSuggestions) return [];
  const lower = prefix.toLowerCase();
  if (lower === '') return operator.valueSuggestions;
  return operator.valueSuggestions.filter((v) => v.toLowerCase().includes(lower));
}
