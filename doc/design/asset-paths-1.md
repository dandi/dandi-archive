# Asset Paths

As DANDI has grown, the assets paths feature has gained use, yet the current implementation is a stopgap solution, that does not scale well. The time has come to support asset paths as first class objects in DANDI. This document outlines the design to support this.

# Requirements

* Delineation between files and folders
* Efficient querying of "folders" (all paths exactly one level underneath the provided path)
* Efficient update of all parent paths upon asset update
  * If assets are added to the version, add them to the assets paths models
  * If assets are removed from the version, remove them from the assets paths model
  * If assets are updated, we must replace the old asset with the new asset, since assets are immutable.
* Store the following on each path
  * The path itself (string)
  * The dandiset version it's associated to
  * The asset that it points to (file), or null (folder).
  * Number of contained assets
  * Aggregate size of these contained assets


# Implementation
The proposed implementation is a [closure table](https://dirtsimple.org/2010/11/simplest-way-to-do-tree-based-queries.html#:~:text=A%20closure%20table%20is%20simply,to%20each%20row's%20parent%20directory.) design. This design involves creating two actual tables.

The first houses the asset paths themselves, along with any data associated with that path (num files, aggregated size, etc). This table will be referred to as the "paths table".

The second houses the relationships between entries in the paths table (parent, child, and depth). This table will be referred to as the "relationship table".

![Asset Paths drawio](https://user-images.githubusercontent.com/11370025/189407081-41de2d18-f650-4aba-adee-6d79b93c1550.png)

This design achieves the following:

## Quick folder queries
This is the simplest operation, only needing to retrieve all rows in the relationship table that have a parent id of x and have a depth of 1.

## Asset insertion
When an asset is added to a version, split the path, and ensure all paths are present in the paths table, adding them (with size, num, etc. of zero) if they're not. This adds a maximum of $n$ new rows to the paths table, where $n$ is the number of paths in that asset, depending on if any paths are already shared by other assets.

Then, for all paths from the above step, increment the size by the asset size, and the number of files by one. This can be done in bulk.

Finally, add all required relations between paths to the relationships table. This is the most intensive step, since each new asset would constitute a maximum of $n^2 + n \over 2$ new rows in the relationship table, depending on what paths are already shared by other assets. For example, if an asset has 4 paths (including the leaf node), there would be a maximum of 10 new rows inserted into the relationship table. Still, this entire insertion can be done in one query.

## Asset deletion
First, find the path (leaf node) that points to the asset in question

Then, query for all paths that are a parent to this leaf node, and decrement their size by the asset size, and the number of files by one. This may leave some paths (and will always leave the leaf node) with a "number of contained assets" equal to zero. So, all of these paths should be deleted as well.

Path deletion is very simple, as if entries in the relationship table are set up to cascade upon the deletion of the referenced path from the paths table, all that's needed is to delete the row in the paths table, and the relationships will also be deleted.

## Asset modification
Since assets are immutable, this will actually entail replacing the existing asset with a new one.

If the path is unchanged, just change the asset ID on the leaf node, and then update all parent paths with the difference in size between the old and new asset.

If the path is changed, perform a deletion, followed by an insertion.


# Caveats
* Upon publish, all paths will need to be copied, using the new version.
* Zarrs should **not** be included in this (they must be browsed separately)
* Signals probably can't be used for these models, since we'll be doing lots of bulk operations. Triggers might prove useful, but we'd need to investigate how to go about this.
* This design constitutes a consider amount of rows in the database.
