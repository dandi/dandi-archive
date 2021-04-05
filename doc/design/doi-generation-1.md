# DOI generation process

## dandi-api

The DOI generation process happens inside a call to `POST /dandisets/{dandiset_id}/draft/publish/`.
DOI generation is the first step of the publish process, because it is the only step to rely on an external service.
If the call to the Datacite API fails, there are no files in S3 that need to be cleaned up.

The API will pass the following to the DOI generator:
* A DOI identifier. This will be of the form `f'{prefix}/{dandiset_id}/{version_id}'`, for example `10.80507/000001/0.210402.1835`.
* A URL for the dandiset. This will be a redirector URL of the form `f'https://dandiarchive.org/dandiset/{dandiset_id}/{version_id}'`.
* The dandiset metadata, as a python dictionary.

## dandi.core.doi ?

This function will generate the body of the DOI and return it.

TODO: fill me in
TODO: what exceptions might be thrown? Missing creator is one.

## dandi-api

* If DOI generation raised any errors, return a 400 error describing the problem.
* Otherwise, attempt to register the DOI identifier/body with Datacite.
* If that raises any errors, log them and return a 400 error.
* Finally, continue with the publish process.
