# Publish process

This process is predicated on a few tasks that are expected to receive valid input and assuming that only certain errors could happen that are out of our control.
Dandisets have a new attribute added to track their validation status: `VALID`, `INVALID`, and `VALIDATING`.
Whenever a dandiset is modified (metadata changed or files uploaded/removed), it is set to `VALIDATING` and an asynchronous task is triggered to run metadata validation on it. The task will update the state of the dandiset accordingly when it finishes.

- publish enabled only if a dandiset is `VALID`. The button will be greyed out in the UI and the API endpoint will return 405.
- on publish trigger:
   - create the versioned release in the db (this prevents any asset/blob belonging to the release from being deleted)
   - insert all the relevant metadata (version, doi, url, manifest location) into the metadata record of the new version
    -  manifest url == dandiarchive api url to GET on assets for the versioned dataset.
  - send this new metadata record to mint the doi (there should be no reason why this should fail unless the external resource fails. if it fails notify admins since this is likely a new bug)
   - write out to s3 bucket (even on any datacite failure)
      - add checksums for dandiset.yaml and assets.yaml which should be stored in a checksums.json in the published directory.

## DOI generation process

## dandi-api

The DOI generation process happens inside a call to `POST /dandisets/{dandiset_id}/draft/publish/`.
DOI generation is the first step of the publish process, because it is the only step to rely on an external service.
If the call to the Datacite API fails, there are no files in S3 that need to be cleaned up.

The API will pass the following to the DOI generator:
* A DOI identifier. This will be of the form `f'{prefix}/{dandiset_id}/{version_id}'`, for example `10.80507/dandi.000001.v0.210402.1835`.
* A URL for the dandiset. This will be a redirector URL of the form `f'https://dandiarchive.org/dandiset/{dandiset_id}/{version_id}'`.
* The dandiset metadata, as a python dictionary.

## dandi.core.to_datacite

This function will generate the body of the DOI and return it.

* creating a mapping between datacite's metadata and datacite's dictionary
  * this should not return an error due to the problems with metadata (should be validated before)

## dandi-api

* If DOI generation raised any errors, return a 400 error describing the problem.
* Otherwise, attempt to register the DOI identifier/body with Datacite.
* If that raises any errors, log them so they are reported in Sentry. Regardless of the outcome, continue with the publish process.
