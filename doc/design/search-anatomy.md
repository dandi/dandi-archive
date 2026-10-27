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

## `anatomy_exact:`

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

Identifiers are compared after normalizing both sides to a canonical CURIE,
`PREFIX:digits` with an uppercase prefix, for the UBERON, MBA, DMBA, HBA, and
DHBA ontologies. The normalization runs in SQL on the stored identifier, so the
archive's mix of PURLs and CURIEs needs no migration.

A name has to match the whole recorded name, so `anatomy_exact:hippocampus`
does not return an entry named "CA1 field of hippocampus".

The second colon in `anatomy_exact:UBERON:0002421` is not ambiguous. Operator
keys are lowercase and the parser splits on the first colon. A bare lowercase
CURIE such as `uberon:0002421` is rejected with a message that suggests
`anatomy_exact:UBERON:0002421`.

Like every other operator, this one combines with AND:
`anatomy_exact:UBERON:0002421 species:mouse`.

## Query

The filter is a single `EXISTS` over `jsonb_array_elements(metadata->'about')`
on `api_version`. A Dandiset matches when one of its versions has an Anatomy
entry that satisfies every anatomy clause.

## Next Step

An `anatomy:` operator that also returns the parts of a region, and for a UBERON
term the corresponding regions of the Allen atlases, needs the ontology graph in
the database. That is proposed separately so this operator can be reviewed on
its own.
