/**
 * Operator catalog for the dandiset list's advanced-search autocomplete.
 *
 * Mirrors the backend allowlist in
 * `dandiapi/api/services/search/operators.py` — keep in sync. The backend is
 * the source of truth (it validates and returns "Did you mean?" suggestions
 * for unknown keys); this file only powers the autocomplete UX.
 *
 * `valueExample` is shown alongside the operator name so users can see at a
 * glance what kind of value to type.
 */

export interface SearchOperator {
  name: string;
  description: string;
  valueExample: string;
}

export const OPERATORS: SearchOperator[] = [
  // Date range
  { name: 'created_after', description: 'Created on or after a date', valueExample: '2024-01-01' },
  { name: 'created_before', description: 'Created before a date', valueExample: '2024-01-01' },
  { name: 'modified_after', description: 'Last modified on or after a date', valueExample: '2024-01-01' },
  { name: 'modified_before', description: 'Last modified before a date', valueExample: '2024-01-01' },
  { name: 'published_after', description: 'Most recent publication on or after', valueExample: '2024-01-01' },
  { name: 'published_before', description: 'Most recent publication before', valueExample: '2024-01-01' },
  // Asset content
  { name: 'species', description: 'Has assets attributed to a species', valueExample: 'mouse' },
  { name: 'approach', description: 'Has assets using an approach', valueExample: 'electrophysiology' },
  { name: 'technique', description: 'Has assets using a measurement technique', valueExample: '"spike sorting"' },
  { name: 'standard', description: 'Has assets in a data standard', valueExample: 'nwb' },
  { name: 'file_type', description: 'Has assets of a file type', valueExample: 'nwb' },
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

/**
 * Inspect `text` and find the token straddling `cursor` (the index where the
 * caret sits). A "token" here is a maximal run of non-whitespace characters
 * — the same boundaries the backend parser uses to split tokens before
 * recognizing operator vs free text.
 *
 * Returns the token's text and its [start, end) range so a caller can
 * splice a replacement back in at the right place.
 */
export interface TokenAtCursor {
  text: string;
  start: number;
  end: number;
}

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
 * Decide whether the autocomplete dropdown should be shown for `token`, and
 * if so which prefix to filter by.
 *
 * - Empty token (cursor in whitespace, or empty input) → show all operators.
 * - Token containing `:` → user is past the operator key, into the value;
 *   suppress autocomplete (we don't suggest values yet).
 * - Otherwise → filter operator names by case-insensitive prefix match on
 *   the token.
 */
export function suggestionsFor(token: string): SearchOperator[] {
  if (token.includes(':')) return [];
  const prefix = token.toLowerCase();
  if (prefix === '') return OPERATORS;
  return OPERATORS.filter((op) => op.name.startsWith(prefix));
}
