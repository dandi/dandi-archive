# Assets granular search

Implementing graph search for dandisets and assets.

## Triple store

Using `Stardog` for the triple store:
- uses `SPARQL`
- allows for "reasoning"
- ...

Accessing from `dandiarchive`:
```
https://search.dandiarchive.org:5820/
```
(password needed)

## Database

Metadata from Dandisets and assets is combined together in `dandisets_meta`. 
Currently 165K triples.


## Examples of queries

### Dandisets level

- list of awards for Dandisets
```
SELECT DISTINCT ?o ?d WHERE 
{
    ?d a dandi:Dandiset;
       schema:contributor/rdf:rest*/rdf:first ?s .
    ?s a  dandi:Organization ; 
       dandi:awardNumber ?o .
}
``` 

- list of Dandisets contributors
```
SELECT DISTINCT ?o ?d WHERE 
{
    ?d a dandi:Dandiset;
       schema:contributor/rdf:rest*/rdf:first ?s .
    ?s a  dandi:Person ; 
       schema:name ?o .
}
```

### Assets levels

- list of assets for specific species
```
SELECT ?asset  { ?asset a dandi:Asset ;
                  schema:identifier ?id ;
                   prov:wasAttributedTo ?p .
                   ?p a dandi:Participant ;
                      dandi:species ?s .
                   ?s schema:name ?n .
                   FILTER (?n = "Homo sapiens - Human")
                   #FILTER contains( lcase(?n), "homo")
}
```
