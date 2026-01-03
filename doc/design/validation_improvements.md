# Validation Improvements

## The Problem

There are a host of open issues regarding data validation.

The most egregious of these is that it is possible (and indeed, not even difficult) to create an invalid Dandiset, upload it, and publish it to obtain a DOI despite the constituent NWB files being improper in any number of files.

Issues include but are not limited to:
- Using extensions to overload metadata fields used in core metadata digests.
- Missing required metadata fields.
- Incorrectly formatted metadata fields.
- Invalid NWB files (e.g., opening with PyNWB instead of an HDF5 library returns validation errors).

The root cause of much of this is the fact that there is two-fold:
- There are simple, not hidden (though slightly discouraged) CLI flags for bypassing validations at time of upload.
- There is no **server-side validation** of Dandisets contents beyond the simple JSON validity of extracted metadata.



## Secondary Issue

It is a very common issue for the DANDI Helpdesk and info email to receive help requests for users attempting to submit invalid files, without understanding why they are invalid or how to fix this.

The current approach to resolving such issues involves a lot of back-and-forth communication, which is time-consuming for both the Helpdesk and the submitters.

The files can sometimes be difficult to share via other means, the validation output and log files may be hard to find or interpret, and the submitters may not have the technical expertise to resolve the issues on their own.

It can also be a source of great frustration for such users (even those who are experienced developers who have submitted multiple datasets to the archive), and can thus breed discontent within the DANDI community.



## Proposal

To address these issues, I propose the following changes to DANDI philosophy:

1. **Server-side file validation**: Implement comprehensive server-side validation checks for all uploaded Dandisets. This includes the actual running of the `dandi validate` command through our own resources and configurations. This removes any need for 'trust' to be placed upon data submitters.
2. **Allow upload of invalid content**: The final goal of any Dandiset should be to obtain a persistent DOI from publication. This should only be granted if the Dandiset is valid. However, to facilitate the submission process, we should still allow users to upload invalid content. This allows them to use 'draft' mode as a staging area, where they can iteratively fix validation issues prior to being able to publish. This would greatly alleviate Problem 2 as well as certain other challenges often experienced by individuals going through the data standardization process.
3. **Eliminate client-side bypass of validation**: Remove any CLI flags or options that allow users to bypass validation during upload. The CLI can (and should) still warn the user about issues as early in the process as possible, but it should not stop the process entirely (though an interactive prompt to continue may be worth considering). This will improve the user experience considerably.

I further suggest offloading the code logic of DANDI Validation into a separate package that can be maintained independently of the logic for downloading and uploading content.

The effect of these changes would simplify the data submission process, reduce the maintenance burden of the DANDI CLI (which would then focus purely on data transfer to and from the archive), and alleviate a bit of the burden on the DANDI Helpdesk.



## Analytics

The following dashboard shows the results of calling `dandi validate` on all published Dandisets as of early 2026:

In summary, ???% of published Dandisets have validation errors, with the most common issues being:

TODO



## Interaction with 'Data Sunsetting' Policy

If the 'Data Sunsetting' policy is implemented with increased time restrictions on draft state Dandisets (with considerations for embargo), these two policy changes together create a 'ticking clock' on how long data can exist on the archive in between initial submission (with potential invalidations) and final publication.

While this may place increased pressure upon data submitters, it will also prevent stagnation by preventing potentially valuable datasets from lingering in draft state indefinitely.
