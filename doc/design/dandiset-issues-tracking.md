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
- [ ] Initiate documentation in handbook on managing issues of the dandisets
- [ ] Upon creation of a Dandiset on dandi-archive:
  - Create (via Github REST API) a git repository on GitHub in a configured (per instance) organization (referring to as `{organization}` below)
  - Invite all Dandiset owners in Triage role to the dandiset. In Triage scope they can close, label, assign issues. The other actions (e.g. user management) would need to be implemented using [bot].
  - Email them pointing to documentation (item above)
- [ ] Setup https://github.com/{organization} [organization-wide](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file) [`.github/ISSUE_TEMPLATE`](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository#creating-issue-forms) with different templates/types of issues to report
- [ ] DLP: add a button "View/Report Issues" or "Issues" leading to issue Tracker (e.g. [Issues](https://github.com/dandisets/000108/issues) for 000108)
  - Complimentary: dandi-archive could query/cache number of known open issues and include within that button, e.g. have it [(1) Issues](https://github.com/dandisets/000108/issues)
  - Complimentary:  asset-level issues filing in UI context menu per file, would pre-fill in the asset path
- [ ] Optional: provide consistent collection of labels to outline typical problems which might occur
  - e.g., `validation-error`, `unable-to-load`, `io-error`, `missing-file`, `permission`, etc.
  - ref: https://github.com/dandi/dandisets/issues/361

### Alternatives considered

#### GitHub, but not inviting users and operating using `@handles`

Although sounded like a good idea at first, cumbersome to implement with consistent and/or desired behavior:

- Dandiset owners would really have no power to do anything, like close the issue etc, unless we implement all such actions (assignment, labeling, etc) via a [bot].
- To ensure that clicking on "New issue" would add needed `@handles` we would need to either
  - add action to monitor new issues to enhance description with the `@handles`, or
  - generate/update issue template per each dandiset with its own list of owners.

### Changes on dandi-archive Backend

- Provision configuration settings for
  - GitHub organization where to create repository for a new dandiset
  - GitHub token with sufficient permissions to create repository in that organization
- If there is provisioned GitHub organization: Job creating a new dandiset entry would trigger a job to create a new repository.

### Changes on dandi-archive Web UI

- If there is provisioned GitHub organization:
    - Add a section to the web UI for each DANDI set for buttons, such as "See issues", "File an issue", "Ask a question" which routes to the corresponding Issues page on the GitHub repo for that DANDI set
    - Buttons or side component could also report the number of questions asked about that DANDI set

### Benefits

- Users already must have a GitHub account to
  - register/login to dandiarchive: we will reuse that same mechanism
  - submit support requests in helpdesk
- GitHub provides a versatile and customizable issue tracking system many of the users might already be familiar with
- In Triage mode dandisets owners would have powers to assign/close issues
- We will make it optional, so if no GitHub organization provisioned, no backend/UI actions/elements.

### Disadvantages

- not "integrated" within dandiarchive.org as issues (meta)data would not be contained within DANDI.
  - A possible mitigation: I guess we could collect mirror issues/comments etc from GitHub internally in the archive. There are tools which could even be used to help. E.g. @yarikoptic has experience with using https://github.com/MichaelMure/git-bug to sync all issues from GitHub locally to collect all contributors to the project. E.g. [this script](https://github.com/nipy/heudiconv-joss-paper/blob/main/authors/tools/make-summaries#L92) processes a JSON dump of all issues from `git bug`  mirror.

[bot]: https://github.com/dandi/dandisets/issues/360
