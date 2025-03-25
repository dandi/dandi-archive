# Rename "staging" to "sandbox"

We have long referred to our test deployment of the DANDI Archive as “staging”. This is due to our deployment workflow, which auto-deploys whatever is on `master` to https://gui-staging.dandiarchive.org, allowing us to test features in a production-like environment before they are deployed to actual production. We have additionally advertised this deployment to archive users as a way to try things out in a safe area before doing real work on the production instance.

The latter usage has led to user confusion about the role of the staging deployment. Specifically, the name “staging” makes people think that they are supposed to put data here for review and cleaning, etc., before it makes its way to a more permanent home somewhere.

To avoid that confusion, we are changing the name of this deployment from “staging” to “sandbox”, better reflecting the end user experience of this deployment. Despite the name change, we will continue to use our deployment strategy without any changes.

## Requirements

The following changes will be required to make this name change happen.

1. **New URL for sandbox deployment.** The deployment formerly known as “staging” will be accessible at `https://sandbox.dandiarchive.org`.
2. **New URL for sandbox API.** The corresponding Django API app will be accessible at `https://api.sandbox.dandiarchive.org`.
3. **Redirections for old URLs.** To prevent user pain, we will redirect requests to the old application and API URLs to the new ones:
    1. [`https://gui-staging.dandiarchive.org`](https://gui-staging.dandiarchive.org) → `https://sandbox.dandiarchive.org`
    2. [`https://api-staging.dandiarchive.org`](https://api-staging.dandiarchive.org) → [`https://api.sandbox.dandiarchive.org`](https://api.sandbox.dandiarchive.org) (using HTTP 308 to preserve the request method)

    The second redirection is probably less important for end users (excluding those that have written, e.g., Python scripts using the DANDI API against staging/sandbox for some reason), but it is necessary to avoid deprecating all previous versions of the DANDI CLI tool which still presumably references the old URLs.
    We will plan to run the redirections indefinitely, though, at any point in the future, we can retire them after announcing our intention to do so.
4. **Application code updates to use the new URLs.** Any references to the old URLs within Vue or Django application code must be updated to the new ones.
5. **Userbase notification.** We need to inform users about the URL change.
6. **Update documentation.** The documentation ecosystem must be updated to refer only to the new URLs and the new name of the deployment.
7. **Update ecosystem tooling.** We need to make sure the rest of the DANDI ecosystem (DANDI Hub, DANDI CLI, etc.) continues functioning normally.
