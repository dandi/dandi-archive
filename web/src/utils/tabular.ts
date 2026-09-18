/**
 * Helpers for recognizing and parsing delimited text assets (.csv/.tsv) so that
 * they can be displayed as a table in the file browser.
 */

export type Delimiter = ',' | '\t';

const TABULAR_EXTENSIONS: Record<string, Delimiter> = {
  csv: ',',
  tsv: '\t',
};

/**
 * Return the delimiter to use for the given path, or null if the path isn't a
 * supported tabular file.
 */
export function tabularDelimiter(path: string): Delimiter | null {
  const extension = path.split('.').pop()?.toLowerCase();
  if (extension === undefined) {
    return null;
  }
  return TABULAR_EXTENSIONS[extension] ?? null;
}

export function isTabularFile(path: string): boolean {
  return tabularDelimiter(path) !== null;
}

/**
 * Whether a cell value is a URL that should be rendered as a link.
 *
 * Deliberately limited to http(s) so that cell contents can't produce
 * `javascript:` or `data:` links.
 */
export function isUrl(value: unknown): boolean {
  if (typeof value !== 'string') {
    return false;
  }
  try {
    const { protocol } = new URL(value.trim());
    return protocol === 'http:' || protocol === 'https:';
  } catch {
    return false;
  }
}

/**
 * Parse delimited text into a matrix of cells.
 *
 * Supports RFC 4180 style quoting, i.e. fields wrapped in double quotes may
 * contain the delimiter, newlines, and doubled-up quotes as escapes.
 */
export function parseDelimitedText(text: string, delimiter: Delimiter): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = '';
  let quoted = false;
  // Tracks whether anything (including an empty field) has been seen on this
  // row, so that trailing newlines don't produce a spurious empty row.
  let rowStarted = false;

  const endField = () => {
    row.push(field);
    field = '';
    rowStarted = true;
  };
  const endRow = () => {
    endField();
    rows.push(row);
    row = [];
    rowStarted = false;
  };

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];

    if (quoted) {
      if (char === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i += 1;
        } else {
          quoted = false;
        }
      } else {
        field += char;
      }
    } else if (char === '"' && field === '') {
      quoted = true;
      rowStarted = true;
    } else if (char === delimiter) {
      endField();
    } else if (char === '\n') {
      endRow();
    } else if (char === '\r') {
      // Swallow CR; the following LF (if any) terminates the row.
      if (text[i + 1] !== '\n') {
        endRow();
      }
    } else {
      field += char;
    }
  }

  if (field !== '' || rowStarted) {
    endRow();
  }

  return rows;
}
