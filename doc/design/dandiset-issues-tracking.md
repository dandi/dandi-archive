# Dandiset issues reporting/tracking

Dandisets could have issues related to problems with

- uploaded data files
- metadata records
- missing files
- validation errors
- fix/enhancement proposals
- etc.

We need to enable an easy and consistent interface to allow archive users to search, report, followup, signup etc to them.
Overall, we need an issue tracking system, while avoiding creating one from scratch.

## Current Process

Largely not formalized:

- DLP does not have any pointer to report an issue for Dandisets
  - footer has overall link to report issues for the archive (and incorrect: [PR to fix](https://github.com/dandi/dandi-archive/pull/1594))
- We generally refer people to [helpdesk discussions](https://github.com/dandi/helpdesk/discussions) as common place to report issues
- While preparing DataLad versions of the Dandisets and posting them on GitHub we do not disable `Issues` feature:
  - for some Dandisets, e.g. https://github.com/dandisets/000108/issues we already used GitHub issues
  - we do not anyhow automatically add/invite original uploaders to those dandisets.
    - note: ATM we do not collect audit information on who specifically uploaded any asset to reliably deduce github users to assign.
- The issue discussing this: https://github.com/dandi/dandi-archive/issues/863


## Proposed Process

**Overall**: Reuse existing Dandisets on GitHub (https://github.com/dandisets), and available for them GitHub's issue tracker.

- [x] Enable Issue tracking per Dandiset.
  - In the process of creating DataLad Dandisets on GitHub we already enable `Issues` functionality for all dandisets.
- [ ] Upon creation of a DataLad Dandiset on GitHub, email the Dandiset owner inviting them to subscribe to the issue tracker on GitHub
- [ ] Setup https://github.com/dandisets [organization-wide](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file) [`.github/ISSUE_TEMPLATE`](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository#creating-issue-forms) with different templates/types of issues to report
- [ ] DLP: add a button "View/Report Issues" or "Issues" leading to issue Tracker (e.g. [Issues](https://github.com/dandisets/000108/issues) for 000108)
  - Complimentary/alternative: Could be "File an issue" button which would prefeed some issue body with `@dandiset-owner` handles etc.  But we might then need to introduce our own UI to choose among different types of issues
  - Optionally: dandi-archive could query/cache number of known open issues and include within that button, e.g. have it [(1) Issues](https://github.com/dandisets/000108/issues)
  - Complimentary:  asset-level issues filing in UI context menu per file, would pre-fill in the asset path
- [ ] Optional: provide consistent collection of labels to outline typical problems which might occur
  - e.g., `validation-error`, `unable-to-load`, `io-error`, `missing-file`, `permission`, etc.
### Changes on dandi-archive Web UI

- Add a section to the web UI for each DANDI set for buttons, such as "See issues", "File an issue", "Ask a question" which routes to the corresponding Issues page on the GitHub repo for that DANDI set
- Buttons or side component could also report the number of questions asked about that DANDI set
### Benefits

- Users already must have a GitHub account to
  - register/login to dandiarchive: we will reuse that same mechanism
  - submit support requests in helpdesk
- GitHub provides a versatile and customizable issue tracking system many of the users might already be familiar with

### Disadvantages

- not "integrated" within dandiarchive.org
  - A possible mitigation: I guess we could collect mirror issues/comments etc from GitHub internally in the archive. There are tools which could even be used to help. E.g. @yarikoptic has experience with using https://github.com/MichaelMure/git-bug to sync all issues from GitHub locally to collect all contributors to the project. E.g. [this script](https://github.com/nipy/heudiconv-joss-paper/blob/main/authors/tools/make-summaries#L92) processes a JSON dump of all issues from `git bug`  mirror.
