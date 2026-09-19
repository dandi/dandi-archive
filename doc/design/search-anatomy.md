# Anatomy Search Operators

This document describes the `anatomy:` and `anatomy_exact:` operators of the
Dandiset search box. The goal is that a user can name a brain region and find
every Dandiset recorded in that region, including Dandisets labeled with a part
of the region or with the corresponding term of a different atlas.

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

The operator names the metadata field and the value carries the ontology, so one
operator covers every ontology and new atlases do not add new operators.

| Query | Meaning |
|---|---|
| `anatomy:hippocampus` | Look the name up as a label or synonym |
| `anatomy:"primary motor cortex"` | Multi-word names are quoted |
| `anatomy:UBERON:0002421`, `anatomy:MBA:1089` | CURIE |
| `anatomy:UBERON_0002421` | Underscore form |
| `anatomy:http://purl.obolibrary.org/obo/UBERON_0002421` | Term URL |
| `anatomy_exact:...` | Any of the above, with no expansion |

The second colon in `anatomy:UBERON:0002421` is not ambiguous. Operator keys are
lowercase and the parser splits on the first colon. A bare lowercase CURIE such
as `uberon:0002421` is rejected with a message that suggests
`anatomy:UBERON:0002421`, and a bare URL is treated as free text.

Like every other operator, these combine with AND:
`anatomy:hippocampus species:mouse`.

## Expansion

`anatomy:` matches the named term, every term inside it, and the equivalent
regions of the other atlases with their own sub-regions. "Inside" means
reachable through `is_a` or `part_of`. Both are needed: in UBERON the
hippocampal formation has no `is_a` descendants and more than a hundred
`part_of` descendants.

Expansion only goes downward. A Dandiset labeled "brain" is not a result for
`anatomy:hippocampus`, because most of what was recorded in the brain was not
recorded in the hippocampus.

The ontologies are UBERON, which is the cross-species reference, and the Allen
atlas ontologies published by BICAN: MBA (adult mouse), DMBA (developing mouse),
HBA (adult human), and DHBA (developing human). The atlas ontologies assert
their own links to UBERON (`MBA_1089 is_a UBERON_0002421`), and UBERON's xrefs
fill in where they do not. Those links make every atlas region a descendant of
its UBERON counterpart, so a UBERON search reaches atlas-labeled data.

The reverse direction is limited to one-to-one pairings. `MBA:1089` and
`UBERON:0002421` are paired one-to-one, so a search on either finds data labeled
with the other. Where several atlas regions map to the same UBERON term, the
UBERON term is broader than each of them, and treating it as their equivalent
would let a search on a small region return data from a larger one.

The atlases do not always agree with UBERON about what contains what. The mouse
atlas places the lateral septal complex inside the striatum and UBERON does not,
so `anatomy:striatum` returns Dandisets labeled with the lateral septal complex.
We accept the union of the hierarchies. `anatomy_exact:` is available when that
is too broad.

## Matching by Name

A value that is not an identifier is resolved to terms by case-insensitive exact
match on label or synonym, and by substring of the label if nothing matches
exactly. The same value is also compared with the recorded `name` of each
Anatomy entry, as whole words, but only for entries whose identifier is missing
or unknown to the ontology tables. An entry with a known identifier is judged by
the identifier alone. This keeps "hypothalamus" out of the results for
`anatomy:thalamus` while still finding the entries that have only a name. It
also means the operator degrades to name and literal identifier matching on an
installation whose ontology tables have not been loaded.

## Storage and Query

Two tables in the `search` app hold the ontology graph. `OntologyTerm` has the
canonical CURIE, IRI, label, and the lowercased label and synonyms.
`OntologyClosure` has one row per (ancestor, descendant) pair, including each
term paired with itself. With the five ontologies above this is about 24,000
terms and 1.3 million closure rows.

`manage.py load_anatomy_ontologies` downloads the obographs JSON releases,
computes the closure, and replaces both tables in one transaction. It takes
about twenty seconds. A Celery beat entry runs the same code monthly. The
command must be run once after deployment.

The filter is a single `EXISTS` over `jsonb_array_elements(metadata->'about')`
on `api_version`, which normalizes each identifier to a CURIE in SQL and joins
it to the closure. `api_version` is small, and against a copy of the production
anatomy metadata the queries ran in 20 to 100 ms.

## Future Work

Coverage is the main limitation: about one Dandiset in ten has an Anatomy entry.
The asset-level path is for dandi-cli to write anatomy into asset metadata from
the location fields of NWB files, and for dandischema to aggregate it into
`assetsSummary.anatomy`. The filter reads its entries from one JSON array, so
adding a second array is a small change. The `anatomical-ontologies` branch
holds a design document for the ingestion side.

Two smaller items would help users. The search field could autocomplete anatomy
values from `OntologyTerm` once a token starts with `anatomy:`, showing the label
and CURIE. The metadata editor could normalize identifiers to one form on save.
