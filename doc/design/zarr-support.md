The Zarr format is being used by NGFF to support the next generation of microscopy data. This involves a potentially 
nested folder structure with named files inside the folder. In the DANDI this would mean:

1. An asset is associated with a single zarr folder. From a user perspective this is still a single asset and the UI 
   should not try to delve into the structure of the folder. The CLI should be able to download the entire tree. Matt
   at kitware is looking into IPFS + NGFF, so we should at least keep that in mind.
3. Blob store allows for a folder, which contains the zarr named "locations" and data. That is given a root prefix, 
   a zarr-compliant software can navigate the zarr metadata/structure using relative path rules.
3. Blob url should continue to point to a single location (i.e. the prefix ending with `/` common to all keys for zarr files) in an s3 bucket instead of a collection of files.
4. The `etag` connected with the zarr file should be a tree-hash of dandi-etags of the folder.

Storing each sub-file of a zarr "dataset" as an asset seems like an overkill without any specific gain at this point. 

Given these considerations here are questions for implementation
1. Is there a way to upload a folder to a given prefix using an API key without having to create 100k signed URLs?
1. Should the tree structure be stored somewhere so that diffs can be ascertained?
1. Given that each zarr file may contain 100k+ files, how will dandi-cli handle alterations?    
