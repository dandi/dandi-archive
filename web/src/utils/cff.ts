import type { DandisetMetadata, Person, Organization } from '@/types';

export interface CFFAuthor {
  given_names?: string;
  family_names?: string;
  name?: string; // For organizations
  orcid?: string;
  email?: string;
  affiliation?: string;
}

export interface CFF {
  'cff-version': string;
  message: string;
  type: string;
  title: string;
  abstract?: string;
  authors: CFFAuthor[];
  identifiers?: Array<{
    type: 'doi' | 'url';
    value: string;
    description?: string;
  }>;
  doi?: string;
  url?: string;
  repository?: string;
  keywords?: string[];
  license?: string;
  version?: string;
  'date-released'?: string;
  references?: Array<{
    type: string;
    title?: string;
    authors?: CFFAuthor[];
    doi?: string;
    url?: string;
  }>;
}

/**
 * Convert a DANDI Person contributor to CFF Author format
 */
function personToCFFAuthor(person: Person): CFFAuthor {
  const nameParts = person.name.split(',').map(s => s.trim());
  const author: CFFAuthor = {};

  if (nameParts.length >= 2) {
    author.family_names = nameParts[0];
    author.given_names = nameParts.slice(1).join(' ');
  } else {
    // If no comma, assume it's all given names
    author.given_names = person.name;
  }

  if (person.identifier) {
    author.orcid = person.identifier.replace('ORCID:', '').replace('https://orcid.org/', '');
  }

  if (person.email) {
    author.email = person.email;
  }

  if (person.affiliation && person.affiliation.length > 0) {
    author.affiliation = person.affiliation.map(aff => aff.name).join('; ');
  }

  return author;
}

/**
 * Convert a DANDI Organization contributor to CFF Author format
 */
function organizationToCFFAuthor(org: Organization): CFFAuthor {
  const author: CFFAuthor = {
    name: org.name || 'Unknown Organization'
  };

  if (org.email) {
    author.email = org.email;
  }

  return author;
}

/**
 * Convert DANDI dandiset metadata to CFF format
 */
export function dandisetToCFF(metadata: DandisetMetadata, doi?: string): CFF {
  const cff: CFF = {
    'cff-version': '1.2.0',
    message: 'If you use this dataset, please cite it as below.',
    type: 'dataset',
    title: metadata.name,
    authors: []
  };

  // Add abstract/description
  if (metadata.description) {
    cff.abstract = metadata.description;
  }

  // Convert contributors who should be included in citation
  metadata.contributor.forEach(contributor => {
    if (contributor.includeInCitation !== false) {
      if (contributor.schemaKey === 'Person') {
        cff.authors.push(personToCFFAuthor(contributor as Person));
      } else if (contributor.schemaKey === 'Organization') {
        cff.authors.push(organizationToCFFAuthor(contributor as Organization));
      }
    }
  });

  // Add identifiers
  cff.identifiers = [];

  if (doi) {
    cff.doi = doi;
    cff.identifiers.push({
      type: 'doi',
      value: doi,
      description: 'Digital Object Identifier'
    });
  }

  if (metadata.identifier) {
    cff.identifiers.push({
      type: 'url',
      value: `https://dandiarchive.org/dandiset/${metadata.identifier}`,
      description: 'DANDI Archive URL'
    });
  }

  // Add URL
  if (metadata.url) {
    cff.url = metadata.url;
  } else if (doi) {
    cff.url = `https://doi.org/${doi}`;
  } else if (metadata.identifier) {
    cff.url = `https://dandiarchive.org/dandiset/${metadata.identifier}`;
  }

  // Add repository
  if (metadata.repository) {
    cff.repository = metadata.repository;
  }

  // Add keywords
  if (metadata.keywords && metadata.keywords.length > 0) {
    cff.keywords = metadata.keywords;
  }

  // Add license
  if (metadata.license && metadata.license.length > 0) {
    // Convert SPDX license identifiers to simple format
    cff.license = metadata.license.map(l => l.replace('spdx:', '')).join(', ');
  }

  // Add version
  if (metadata.version) {
    cff.version = metadata.version;
  }

  // Add release date
  if (metadata.dateModified) {
    cff['date-released'] = metadata.dateModified.split('T')[0]; // Extract date part
  }

  // Add related resources as references
  if (metadata.relatedResource && metadata.relatedResource.length > 0) {
    cff.references = metadata.relatedResource.map(resource => {
      const ref: any = {
        type: mapResourceTypeToCFF(resource.resourceType),
      };

      if (resource.name) {
        ref.title = resource.name;
      }

      if (resource.identifier && resource.identifier.startsWith('doi:')) {
        ref.doi = resource.identifier.replace('doi:', '');
      }

      if (resource.url) {
        ref.url = resource.url;
      }

      return ref;
    });
  }

  return cff;
}

/**
 * Map DANDI resource types to CFF reference types
 */
function mapResourceTypeToCFF(resourceType?: string): string {
  const mapping: Record<string, string> = {
    'dcite:JournalArticle': 'article',
    'dcite:ConferencePaper': 'conference-paper',
    'dcite:Book': 'book',
    'dcite:Dataset': 'dataset',
    'dcite:Software': 'software',
    'dcite:Report': 'report',
    'dcite:Dissertation': 'thesis',
  };

  return mapping[resourceType || ''] || 'generic';
}

/**
 * Convert CFF to BibTeX format
 */
export function cffToBibTeX(cff: CFF, identifier: string): string {
  const type = '@dataset';
  const key = `dandi:${identifier.replace('/', '_')}`;

  const authors = cff.authors.map(author => {
    if (author.name) {
      return `{${author.name}}`;
    }
    return `${author.family_names || ''}, ${author.given_names || ''}`.trim();
  }).join(' and ');

  let bibtex = `${type}{${key},\n`;
  bibtex += `  title = {${cff.title}},\n`;
  bibtex += `  author = {${authors}},\n`;

  if (cff.doi) {
    bibtex += `  doi = {${cff.doi}},\n`;
  }

  if (cff.url) {
    bibtex += `  url = {${cff.url}},\n`;
  }

  if (cff.abstract) {
    bibtex += `  abstract = {${cff.abstract.replace(/\n/g, ' ')}},\n`;
  }

  if (cff.keywords) {
    bibtex += `  keywords = {${cff.keywords.join(', ')}},\n`;
  }

  if (cff.version) {
    bibtex += `  version = {${cff.version}},\n`;
  }

  if (cff['date-released']) {
    const year = cff['date-released'].split('-')[0];
    bibtex += `  year = {${year}},\n`;
  }

  bibtex += `  publisher = {DANDI Archive},\n`;
  bibtex += `  note = {DANDI:${identifier}}\n`;
  bibtex += '}';

  return bibtex;
}

/**
 * Convert CFF to APA format (7th edition)
 */
export function cffToAPA(cff: CFF): string {
  const authors = cff.authors.map((author) => {
    if (author.name) {
      return author.name;
    }

    const initials = author.given_names
      ?.split(/\s+/)
      .map(name => name.charAt(0).toUpperCase() + '.')
      .join(' ');

    return `${author.family_names}, ${initials}`;
  });

  let authorString = '';
  if (authors.length === 1) {
    authorString = authors[0];
  } else if (authors.length === 2) {
    authorString = `${authors[0]} & ${authors[1]}`;
  } else {
    authorString = authors.slice(0, -1).join(', ') + ', & ' + authors[authors.length - 1];
  }

  const year = cff['date-released'] ? ` (${cff['date-released'].split('-')[0]})` : '';
  const version = cff.version ? ` (Version ${cff.version})` : '';
  const doi = cff.doi ? ` https://doi.org/${cff.doi}` : '';

  return `${authorString}${year}. ${cff.title}${version} [Data set]. DANDI Archive.${doi}`;
}

/**
 * Convert CFF to MLA format (9th edition)
 */
export function cffToMLA(cff: CFF): string {
  const authors = cff.authors.map((author, index) => {
    if (author.name) {
      return author.name;
    }

    if (index === 0) {
      // First author: Last, First
      return `${author.family_names}, ${author.given_names}`;
    }
    // Subsequent authors: First Last
    return `${author.given_names} ${author.family_names}`;
  });

  let authorString = '';
  if (authors.length === 1) {
    authorString = authors[0];
  } else if (authors.length === 2) {
    authorString = `${authors[0]}, and ${authors[1]}`;
  } else if (authors.length === 3) {
    authorString = `${authors[0]}, ${authors[1]}, and ${authors[2]}`;
  } else {
    authorString = `${authors[0]}, et al`;
  }

  const year = cff['date-released'] ? cff['date-released'].split('-')[0] : 'n.d.';
  const doi = cff.doi ? ` doi:${cff.doi}` : '';

  return `${authorString}. "${cff.title}." DANDI Archive, ${year}.${doi}`;
}

/**
 * Convert CFF to Chicago format (17th edition, Author-Date)
 */
export function cffToChicago(cff: CFF): string {
  const authors = cff.authors.map((author, index) => {
    if (author.name) {
      return author.name;
    }

    if (index === 0) {
      // First author: Last, First
      return `${author.family_names}, ${author.given_names}`;
    }
    // Subsequent authors: First Last
    return `${author.given_names} ${author.family_names}`;
  });

  let authorString = '';
  if (authors.length === 1) {
    authorString = authors[0];
  } else if (authors.length <= 3) {
    authorString = authors.slice(0, -1).join(', ') + ', and ' + authors[authors.length - 1];
  } else {
    authorString = `${authors[0]} et al.`;
  }

  const year = cff['date-released'] ? cff['date-released'].split('-')[0] : 'n.d.';
  const version = cff.version ? `, version ${cff.version}` : '';
  const doi = cff.doi ? ` https://doi.org/${cff.doi}` : '';

  return `${authorString}. ${year}. "${cff.title}." Data set${version}. DANDI Archive.${doi}`;
}

/**
 * Convert CFF to Harvard format
 */
export function cffToHarvard(cff: CFF): string {
  const authors = cff.authors.map((author) => {
    if (author.name) {
      return author.name;
    }

    const initials = author.given_names
      ?.split(/\s+/)
      .map(name => name.charAt(0).toUpperCase() + '.')
      .join('');

    return `${author.family_names}, ${initials}`;
  });

  let authorString = '';
  if (authors.length === 1) {
    authorString = authors[0];
  } else if (authors.length === 2) {
    authorString = `${authors[0]} and ${authors[1]}`;
  } else if (authors.length === 3) {
    authorString = `${authors[0]}, ${authors[1]} and ${authors[2]}`;
  } else {
    authorString = `${authors[0]} et al.`;
  }

  const year = cff['date-released'] ? cff['date-released'].split('-')[0] : 'n.d.';
  const doi = cff.doi ? ` Available at: https://doi.org/${cff.doi}` : '';

  return `${authorString} (${year}) '${cff.title}', DANDI Archive. Data set.${doi}`;
}

/**
 * Convert CFF to Vancouver format (used in biomedical sciences)
 */
export function cffToVancouver(cff: CFF): string {
  const authors = cff.authors.map((author) => {
    if (author.name) {
      return author.name;
    }

    const initials = author.given_names
      ?.split(/\s+/)
      .map(name => name.charAt(0).toUpperCase())
      .join('');

    return `${author.family_names} ${initials}`;
  });

  // Vancouver limits to 6 authors, then "et al."
  let authorString = '';
  if (authors.length <= 6) {
    authorString = authors.join(', ');
  } else {
    authorString = authors.slice(0, 6).join(', ') + ', et al';
  }

  const year = cff['date-released'] ? cff['date-released'].split('-')[0] : '';
  const doi = cff.doi ? ` doi: ${cff.doi}` : '';

  return `${authorString}. ${cff.title} [Data set]. DANDI Archive; ${year}.${doi}`;
}

/**
 * Convert CFF to IEEE format
 */
export function cffToIEEE(cff: CFF): string {
  const authors = cff.authors.map((author) => {
    if (author.name) {
      return author.name;
    }

    const initials = author.given_names
      ?.split(/\s+/)
      .map(name => name.charAt(0).toUpperCase() + '.')
      .join(' ');

    return `${initials} ${author.family_names}`;
  });

  let authorString = '';
  if (authors.length === 1) {
    authorString = authors[0];
  } else if (authors.length === 2) {
    authorString = `${authors[0]} and ${authors[1]}`;
  } else {
    authorString = authors.slice(0, -1).join(', ') + ', and ' + authors[authors.length - 1];
  }

  const year = cff['date-released'] ? cff['date-released'].split('-')[0] : '';
  const doi = cff.doi ? ` doi: ${cff.doi}` : '';

  return `${authorString}, "${cff.title}," DANDI Archive, ${year}.${doi}`;
}

/**
 * Convert CFF to RIS format
 */
export function cffToRIS(cff: CFF, identifier: string): string {
  let ris = 'TY  - DATA\n';
  ris += `TI  - ${cff.title}\n`;

  cff.authors.forEach(author => {
    if (author.name) {
      ris += `AU  - ${author.name}\n`;
    } else {
      ris += `AU  - ${author.family_names || ''}, ${author.given_names || ''}\n`;
    }
  });

  if (cff.abstract) {
    ris += `AB  - ${cff.abstract.replace(/\n/g, ' ')}\n`;
  }

  if (cff.keywords) {
    cff.keywords.forEach(keyword => {
      ris += `KW  - ${keyword}\n`;
    });
  }

  if (cff.doi) {
    ris += `DO  - ${cff.doi}\n`;
  }

  if (cff.url) {
    ris += `UR  - ${cff.url}\n`;
  }

  if (cff['date-released']) {
    const dateParts = cff['date-released'].split('-');
    ris += `PY  - ${dateParts[0]}\n`;
    if (dateParts[1]) ris += `Y2  - ${dateParts[0]}/${dateParts[1]}/${dateParts[2] || '01'}\n`;
  }

  ris += 'PB  - DANDI Archive\n';
  ris += `N1  - DANDI:${identifier}\n`;

  if (cff.version) {
    ris += `VL  - ${cff.version}\n`;
  }

  ris += 'ER  -\n';

  return ris;
}

/**
 * Convert CFF to YAML string
 */
export function cffToYAML(cff: CFF): string {
  // Simple YAML serialization (could be replaced with a proper YAML library)
  return stringifyYAML(cff, 0);
}

function stringifyYAML(obj: any, indent: number = 0): string {
  const spaces = '  '.repeat(indent);
  let yaml = '';

  for (const [key, value] of Object.entries(obj)) {
    if (value === undefined || value === null) continue;

    yaml += `${spaces}${key}:`;

    if (typeof value === 'string') {
      // Quote strings that contain special characters
      if (value.includes(':') || value.includes('\n') || value.includes('"') || value.includes("'")) {
        yaml += ` "${value.replace(/"/g, '\\"').replace(/\n/g, '\\n')}"\n`;
      } else {
        yaml += ` ${value}\n`;
      }
    } else if (typeof value === 'number' || typeof value === 'boolean') {
      yaml += ` ${value}\n`;
    } else if (Array.isArray(value)) {
      if (value.length === 0) {
        yaml += ' []\n';
      } else if (typeof value[0] === 'string' || typeof value[0] === 'number') {
        // Simple array
        yaml += '\n';
        value.forEach(item => {
          yaml += `${spaces}  - ${item}\n`;
        });
      } else {
        // Array of objects - use inline format for first property
        yaml += '\n';
        value.forEach(item => {
          const entries = Object.entries(item).filter(([, v]) => v !== undefined && v !== null);
          if (entries.length > 0) {
            const [firstKey, firstValue] = entries[0];
            yaml += `${spaces}  - ${firstKey}: ${formatYAMLValue(firstValue)}\n`;
            // Remaining properties
            for (let i = 1; i < entries.length; i++) {
              const [k, v] = entries[i];
              yaml += `${spaces}    ${k}: ${formatYAMLValue(v)}\n`;
            }
          }
        });
      }
    } else if (typeof value === 'object') {
      yaml += '\n';
      yaml += stringifyYAML(value, indent + 1);
    }
  }

  return yaml;
}

function formatYAMLValue(value: any): string {
  if (typeof value === 'string') {
    if (value.includes(':') || value.includes('\n') || value.includes('"') || value.includes("'")) {
      return `"${value.replace(/"/g, '\\"').replace(/\n/g, '\\n')}"`;
    }
    return value;
  } else if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  return String(value);
}
