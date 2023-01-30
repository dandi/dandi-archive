# Handling "Test" Dandisets

As we introduce people to the archive, and as we ourselves work on the archive,
we often create "test dandisets" that are (1) devoid of assets and/or (2) are
only meant for exploration and development.

Due to the relative ease of creating a dandiset (to check out the system),
compared to curating a dandiset for actual work, the production instance has
more such test dandisets in it than "real" ones. This in turn degrades the
perception of the archive as a serious place to host data, and so we need some
way to (1) discourage the creation and abandonment of exploratory dandisets; (2)
mark dev dandisets in some way to prevent them from appearing in the main
listing; and (3) clean up the archive from such abandoned dandisets.

## Proposals

### "Test" flag

This proposes to add a `testing` flag to all dandisets. At creation time, a
dandiset can optionally have this flag set to prevent it from showing up in
public listings of all dandisets. These would only show up in the owners' "my
dandisets" listings (or in all listings shown to the owners). Admins would get a
checkmark to toggle the display of test dandisets, to help simulate what other
users are seeing when they visit the archive.

To encourage the use of this feature, the dandiset creation screen would have a
checkbox along with a description of what this is for ("If you are new to the
archive and are just exploring, please consider using the staging server
instead. Otherwise, select this option to avoid this dandiset from appearing in
public searches.", with "staging server" linked thereto).

### Hide draft-only dandisets

Similarly to hiding explicitly marked test dandisets, we could, by default, also
hide dandisets that have no published versions (as above, these dandisets would
still appear for the owners). As the public may *want* to see draft-only
dandisets, everyone would be able to toggle this mode with a setting.

**NOTE: this feature has already been implemented.**

### Hide dandisets with no assets

Another variation on the previous proposal: hide dandisets that contain no
assets. These dandisets are a subset of draft-only dandisets, since publishing a
dandiset requires assets to be present.

This option is problematic on its own--it is a valid use case to declare
scientific intentions by creating a draft dandiset with no assets, then collect
and add data only after months or years of real scientific work. That is to say,
an assetless dandiset that nonetheless has a description, funding agent,
contact person, owners, etc. may indeed be fully valid.

**NOTE: this feature has already been implemented.**

### Add questions to dandiset creation page

Adding questions such as:
- Do you welcome collaborators? (Y/N)
- When do you anticipate posting data to the dandiset?

may help to stem the tide of abandoned dandisets.

The collaborators question, answered positively, would add a badge to the
dandiset's landing page and search result display indicating the call for
collaboration.

The anticipation date question would delay considering the dandiset abandoned
until after that date.

### Enable deletion of dandisets

Part of the problem may be that people simply cannot delete their own abanonded
dandisets. Offering a delete button with the proper semantics could help here.

The archive does not allow for deletion of *published* dandisets, by design. But
dandisets that are draft-only should be deleteable.

And, as an extension to that idea, a published dandiset should be able to be
"sealed" by having its draft dandiset deleted, thus closing it off to further
updates. This would serve as a signal that the dandiset is in its final state
and has become a permanent member of the archive. Owners and admins will be able
to "unseal" sealed dandisets in case further modification is needed.

### Delisting of inactive dandisets

Dandisets in a certain set of conditions will be automatically "delisted",
meaning they will not appear in listings or searches other than to the owners
themselves. Additionally, a delisted dandiset will become read-only so that only
actively listed dandisets can be used by their owners to store data.

Conditions for delisting can include the following:
- draft-only and assetless for more than 7 days
- draft-only and no activity for more than 14 days
- published with no activity for more than 30 days (also see "sealing" above)

Whenever a dandiset becomes inactive according to this definition, it will
automatically become delisted, and an email will be sent to the owners to inform
them thereof.

To relist the dandiset, an owner or admin would log in, navigate to the DLP for
that dandiset, and click on a "relist" button. After some number of relistings,
the option to relist would become disabled, with a note directing them to
contact the admins to discuss what's going on with the dandiset. This relist
countdown can be waived if the owners resume intended usage of the archive to
develop the dandiset, publish it, etc.

This is just a sketch of how this feature might work. It is extremely complex,
requiring policy, careful communication, and buy-in from the community, but
would also bring richness and value to the dandisets hosted on the archive.
