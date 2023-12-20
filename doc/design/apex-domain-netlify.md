# Serving the GUI at dandiarchive.org with Netlify
Currently, the GUI is served at gui.dandiarchive.org, while the apex domain dandiarchive.org is controlled by the redirector. The redirector performs two main tasks

1. Redirect requests from dandiarchive.org to gui.dandiarchive.org
2. Serve JSON information about deployed services (e.g. urls for the API, web ui, and jupyterhub) at dandiarchive.org/server-info.

We've decided that our UI is stable enough to warrant serving it directly at dandiarchive.org, leaving just the task of serving a JSON file containing deployment information. Netlify seems capable of performing this task, and this document outlines the proposal to do so.

## Serving the Deployment JSON file
Netlify cannot specify a different set of redirects for a different build context, so a custom plugin is required. Netlify does support custom JS plugins that hook into the build process and modify the Netlify configuration, so we can use that to specify a different redirect based on the `VITE_APP_DANDI_API_ROOT` environment variable. This redirect will proxy `dandiarchive.org/server-info` to `api.dandiarchive/api/server-info`, or the appropriate domains for staging.

## Backwards Compatibility

To maintain backwards compatibility, old gui.dandiarchive.org URLs should be redirected to dandiarchive.org. This can be trvially achieved by updating our AWS Route53 configuration.
