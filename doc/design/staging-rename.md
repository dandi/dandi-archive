# Rename "staging" to "sandbox"

We have long referred to our test deployment of the DANDI Archive as “staging”. This is due to our deployment workflow, which auto-deploys whatever is on `master` to https://gui-staging.dandiarchive.org, allowing us to test features in a production-like environment before they are deployed to actual production. We have additionally advertised this deployment to archive users as a way to try things out in a safe area before doing real work on the production instance.

The latter usage has led to user confusion about the role of the staging deployment. Specifically, the name “staging” makes people think that they are supposed to put data here for review and cleaning, etc., before it makes its way to a more permanent home somewhere.

To avoid that confusion, we are changing the name of this deployment from “staging” to “sandbox”, better reflecting the end user experience of this deployment. Despite the name change, we will continue to use our deployment strategy without any changes.

## Requirements

The following changes will be required to make this name change happen.

1. **New URL for sandbox deployment.** The deployment formerly known as “staging” will be accessible at `https://sandbox.dandiarchive.org`.
2. **New URL for sandbox API.** The corresponding Django API app will be accessible at `https://api.sandbox.dandiarchive.org`.
3. **Redirection for old web application URL.** To prevent user pain, we will redirect requests to the old application to the new one:
    [`https://gui-staging.dandiarchive.org`](https://gui-staging.dandiarchive.org) → [`https://sandbox.dandiarchive.org`](https://sandbox.dandiarchive.org)

    We will not provide redirects for the API server. Instead, we will release a new version of the DANDI CLI with the updated API URL and deprecate past versions. The S3 bucket name/URL has not changed, so past blob download URLs will continue to work.
    We will plan to run the redirection indefinitely, though, at any point in the future, we can retire it after announcing our intention to do so.
4. **Application code updates to use the new URLs.** Any references to the old URLs within Vue or Django application code must be updated to the new ones.
5. **Userbase notification.** We need to inform users about the URL change.
6. **Update documentation.** The documentation ecosystem must be updated to refer only to the new URLs and the new name of the deployment.
7. **Update ecosystem tooling.** We need to make sure the rest of the DANDI ecosystem (DANDI Hub, DANDI CLI, etc.) continues functioning normally.
