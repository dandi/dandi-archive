Endpoint for Efficiently Querying an Asset or Folder at a Given Path
====================================================================

[`dandidav`](https://github.com/dandi/dandidav), the WebDAV interface to the
DANDI Archive, fetches all of its information about the Archive via the Archive
REST API; unfortunately, the API's support for getting all of the necessary
information about assets & folders at a given path is incredibly suboptimal,
resulting in multiple API requests per WebDAV request, including making a
separate request for each & every asset immediately within a folder.

This design doc therefore proposes the addition of a new endpoint to the
Archive API that can be used to answer all of the following questions in a
single (possibly paginated) request:

- Is the resource at a given path an asset, a folder, or nonexistent?

- If the resource is an asset, what are its properties and, optionally,
  its metadata?

- Optionally, if the resource is a folder, what are all of its children — both
  assets and subfolders — and, for child assets, what are their properties and
  metadata?

Requests
--------

A `GET` endpoint shall be added at
`/dandisets/{dandiset_id}/versions/{version_id}/assets/atpath/`.  The endpoint
shall take the following query parameters:

- `path` — A normalized forward-slash-separated relative path, identifying the
  asset or folder to return information on.

    - If this parameter is absent or empty, the request is for the root
      directory of the Dandiset version's file hierarchy.

    - If the path is present but no resource exists at the given path, a 404
      response is returned.

        - For the purposes of this endpoint, empty folders do not exist.

    - If the path ends in a forward slash and no folder exists at the given
      path, a 404 is returned, even if an asset exists at the path with the
      trailing slash removed.

- `metadata` — Whether to include asset metadata in the response; possible
  values are `0` (the default), indicating that metadata should not be
  included, and `1`, indicating that metadata should be included.

    - Values other than `0` and `1` are treated the same as `0`.

- `children` — Whether to include children of `path` in the response; possible
  values are `0` (the default), indicating that children should not be
  included, and `1`, indicating that children should be included.

    - This parameter has no effect when the resource at `path` is an asset
      rather than a folder.

    - Values other than `0` and `1` are treated the same as `0`.

- `page` and `page_size` — Pagination parameters

Responses
---------

All successful responses from this endpoint shall be structured as a paginated
list, using the same pagination schema as is already used for other endpoints.

- When `path` points to an asset, the list shall contain a single item: a JSON
  object containing the following fields:

    - `"type"` — Always has a value of `"asset"`

    - `"resource"` — A sub-object containing the properties of the asset at
      `path` (i.e., `asset_id`, `blob`, `zarr`, `path`, `size`, `created`, and
      `modified`).  If `metadata=1` was supplied in the request, this
      sub-object shall also contain a `"metadata"` field containing the asset's
      metadata.

- When `path` points to a non-root folder, the first element of the list shall
  be a JSON object containing the following fields:

    - `"type"` — Always has a value of `"folder"`

    - `"resource"` — A sub-object containing the following fields:

        - `"path"` — the path of the folder, without a trailing slash

        - `"total_assets"` — an integer giving the total number of assets in
          this folder and all of its descendants

        - `"total_size"` — an integer giving the total size in bytes of all
          assets in this folder and all of its descendants

  If the `children` parameter was not set to `1` in the request, this is the
  only element of the list.  Otherwise, the rest of the list consists of JSON
  objects for the assets and subfolders immediately within the folder, ordered
  by their paths (without trailing slashes) and sorted in UTF-8 byte-wise
  order.

    - Each asset is represented by an object with the same schema as described
      above for when `path` points to an asset, including `"metadata"` being
      present when `metadata=1` was supplied in the request.

    - Each subfolder is represented by an object with the same schema as
      described above for the folder at `path`.

- When `path` is empty or absent, the list shall be the same as for a folder
  located at the root of the file hierarchy, except that there shall be no
  initial element describing the resource at `path`.  (Hence, if `children` is
  not `1`, the list shall be empty.)

Example
-------

A request for
`/dandisets/000029/versions/0.231017.2004/assets/atpath/?metadata=1&children=1`
would have a response of:

```json
{
    "count": 9,
    "next": null,
    "previous": null,
    "results": [
        {
            "type": "asset",
            "resource": {
                "asset_id": "1ab0d4ff-1231-48c9-a8a3-8145552830a4",
                "blob": "2fd7464f-5459-4c96-a938-27cf13f4d330",
                "zarr": null,
                "path": "bar-renamed-3334",
                "size": 4,
                "created": "2023-09-27T17:08:32.039960Z",
                "modified": "2023-10-17T19:55:40.394757Z",
                "metadata": "--- SNIPPED FOR BREVITY ---"
            }
        },
        {
            "type": "asset",
            "resource": {
                "asset_id": "ad49cd65-184a-4dad-8dde-523e7aaab56c",
                "blob": "56f5b879-e5fa-476c-9893-dab482f66b3d",
                "zarr": null,
                "path": "baz",
                "size": 4,
                "created": "2023-03-16T15:50:06.908811Z",
                "modified": "2023-03-17T15:41:18.403892Z",
                "metadata": "--- SNIPPED FOR BREVITY ---"
            }
        },
        {
            "type": "folder",
            "resource": {
                "path": "sub-anm369962",
                "total_assets": 1,
                "total_size": 6644036
            }
        },
        {
            "type": "folder",
            "resource": {
                "path": "sub-anm369963",
                "total_assets": 1,
                "total_size": 6393196
            }
        },
        {
            "type": "folder",
            "resource": {
                "path": "sub-anm369964",
                "total_assets": 1,
                "total_size": 7660100
            }
        },
        {
            "type": "folder",
            "resource": {
                "path": "sub-monk-g",
                "total_assets": 1,
                "total_size": 18295752
            }
        },
        {
            "type": "folder",
            "resource": {
                "path": "sub-RAT123",
                "total_assets": 1,
                "total_size": 18792
            }
        },
        {
            "type": "asset",
            "resource": {
                "asset_id": "c7913fad-ccc6-467f-a4b6-a9b62af6d98f",
                "blob": "0317cf5a-4047-4e19-aae1-4f7b7434d2d7",
                "zarr": null,
                "path": "test1234",
                "size": 9,
                "created": "2023-03-16T15:50:06.762183Z",
                "modified": "2023-03-17T15:41:18.369626Z",
                "metadata": "--- SNIPPED FOR BREVITY ---"
            }
        },
        {
            "type": "asset",
            "resource": {
                "asset_id": "bb612483-0a97-4309-9763-7fb518265c70",
                "blob": "0317cf5a-4047-4e19-aae1-4f7b7434d2d7",
                "zarr": null,
                "path": "test12345",
                "size": 9,
                "created": "2023-03-16T15:50:07.184996Z",
                "modified": "2023-03-17T15:41:18.378517Z",
                "metadata": "--- SNIPPED FOR BREVITY ---"
            }
        }
    ]
}
```
