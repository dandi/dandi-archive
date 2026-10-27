# Anatomy Search Operators

This document describes the anatomy operators of the Dandiset search box. The
goal is that a user can name a brain region and find the Dandisets recorded
there.

## Where Anatomy Lives Today

Anatomy is recorded in the Dandiset-level `about` field as entries with
`schemaKey: Anatomy`. A survey of the public archive in September 2026 found
such entries on about 120 Dandisets. It is not part of `assetsSummary` and is
almost never present in asset metadata.

The identifiers are written in several ways. Most are OBO PURLs
(`http://purl.obolibrary.org/obo/UBERON_0002421`), a quarter are CURIEs
(`UBERON:0002421`), a few are BICAN PURLs for the Allen atlases
(`https://purl.brain-bican.org/ontology/mbao/MBA_549`), and about thirty entries
have a name and no identifier. Some entries tagged as Anatomy carry cell type,
chemical, or taxon identifiers, which these operators ignore.

## Syntax

There are two operators. `anatomy:` matches a region and everything inside it.
`anatomy_exact:` matches only the region itself.

The operator names the metadata field and the value carries the ontology, so one
operator covers every ontology and new atlases do not add new operators.

| Query | Matches Anatomy entries |
|---|---|
| `anatomy_exact:UBERON:0002421` | with that identifier, in any spelling |
| `anatomy_exact:UBERON_0002421` | the same |
| `anatomy_exact:http://purl.obolibrary.org/obo/UBERON_0002421` | the same |
| `anatomy_exact:MBA:1089` | with that mouse atlas identifier |
| `anatomy_exact:hippocampus` | whose recorded name is "hippocampus", ignoring case |
| `anatomy_exact:"dorsal hippocampus (dHPC)"` | multi-word names are quoted |

`anatomy:` takes the same values.

Identifiers are compared after normalizing both sides to a canonical CURIE,
`PREFIX:digits` with an uppercase prefix, for the UBERON, MBA, DMBA, HBA, and
DHBA ontologies. The normalization runs in SQL on the stored identifier, so the
archive's mix of PURLs and CURIEs needs no migration.

The second colon in `anatomy_exact:UBERON:0002421` is not ambiguous. Operator
keys are lowercase and the parser splits on the first colon. A bare lowercase
CURIE such as `uberon:0002421` is rejected with a message that suggests
`anatomy:UBERON:0002421`.

Like every other operator, these combine with AND:
`anatomy:hippocampus species:mouse`.

## Expansion

`anatomy:` matches the named term and every term inside it. For a UBERON term
that includes the corresponding regions of the species atlases and their
sub-regions. "Inside" means reachable through `is_a` or `part_of`. Both are
needed: in UBERON the hippocampal formation has no `is_a` descendants and more
than a hundred `part_of` descendants.

Expansion only goes downward. A Dandiset labeled "brain" is not a result for
`anatomy:hippocampus`, because most of what was recorded in the brain was not
recorded in the hippocampus.

The ontologies are UBERON, which is the cross-species reference, and the Allen
atlas ontologies published by BICAN: MBA (adult mouse), DMBA (developing mouse),
HBA (adult human), and DHBA (developing human). The atlas ontologies assert
their own links to UBERON (`MBA_1089 is_a UBERON_0002421`), and UBERON's xrefs
fill in where they do not. Those links make every atlas region a descendant of
its UBERON counterpart, so a UBERON search reaches atlas-labeled data.

There is no link in the other direction. An atlas term describes the brain of
one species, so a search on `MBA:1089` returns data labeled with that mouse
atlas region or its sub-regions and nothing else. A user who wants mouse
hippocampus data regardless of how it was labeled should search
`anatomy:UBERON:0002421 species:mouse`.

Results follow the ontologies, including where a reader might not expect it.
UBERON places the lateral septal complex inside the striatum, so
`anatomy:striatum` returns Dandisets labeled with the lateral septal complex.
`anatomy_exact:` is available when the expansion is too broad.

## Matching by Name

A value that is not an identifier is resolved to terms by case-insensitive exact
match on label or synonym, and by substring of the label if nothing matches
exactly. The same value is also compared with the recorded `name` of each
Anatomy entry, but only for entries whose identifier is missing or not in the
ontology tables. An entry with a known identifier is judged by the identifier
alone. For `anatomy:` the name comparison is by whole words, which keeps
"hypothalamus" out of the results for `anatomy:thalamus`. For `anatomy_exact:`
the recorded name has to be the whole value. With empty ontology tables both
operators fall back to literal identifiers and names.

## Storage

Three tables in the `search` app hold the ontology. `OntologyTerm` has the
canonical CURIE, IRI, label, and the lowercased label and synonyms.
`OntologyClosure` has one row per (ancestor, descendant) pair, including each
term paired with itself. `OntologyRelease` records the checksum and source URLs
of each load.

Only the part of UBERON inside the nervous system or the sense organs is kept,
plus every atlas term: 12,717 terms and 286,680 closure rows, against 24,220
terms and about 913,000 rows for the whole of UBERON. Anatomy entries outside
that part still match by literal identifier and by name, without expansion.

## Updating the Ontologies

The source releases are pinned in `dandiapi/search/ontology.py`: UBERON by
release tag and the BICAN atlases by commit. `manage.py build_anatomy_ontology`
downloads them, keeps the terms described above, and writes the terms and their
containment edges to `dandiapi/search/data/anatomy_ontology.json.gz` (about
300 KB). The output is reproducible byte for byte. Updating the ontologies is a
pull request that changes the pins and that file, so the change is reviewed and
deployed like code.

Nothing is downloaded in production. After every `migrate`, which runs in the
release phase of each deploy, a `post_migrate` handler compares the packaged
file's checksum with the latest `OntologyRelease` and reloads the tables in one
transaction if they differ. A fresh load takes under 20 seconds; when the file
is unchanged the check is a single query. `manage.py load_anatomy_ontology
--force` reloads by hand. The handler is off in the test settings, where tests
load a small fixture graph.

## Query

The filter is a single `EXISTS` over `jsonb_array_elements(metadata->'about')`
on `api_version`. A Dandiset matches when one of its versions has an Anatomy
entry that satisfies every anatomy clause.

The closure join adds one `IN` subquery over `search_ontologyclosure`.

## Alternatives

A materialized view that extracts each Dandiset's anatomy CURIEs and their
ancestors into an indexed array, in the style of the existing `asset_search`
view, would move the closure join out of query time. With about 120 Dandisets
carrying anatomy this is not needed yet, but it is the natural place for
asset-level anatomy if dandischema starts aggregating it into
`assetsSummary.anatomy`.

## Future Work

Coverage is the main limitation: about one Dandiset in ten has an Anatomy entry.
The asset-level path is for dandi-cli to write anatomy into asset metadata from
the location fields of NWB files, and for dandischema to aggregate it into
`assetsSummary.anatomy`. The filter reads its entries from one JSON array, so
adding a second array is a small change.

The search field could autocomplete anatomy values from `OntologyTerm` once a
token starts with `anatomy:`, showing the label and CURIE. The metadata editor
could normalize identifiers to one form on save.
