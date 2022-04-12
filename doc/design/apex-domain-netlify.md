# Serving the GUI at dandiarchive.org with Netlify
Currently, the GUI is served at gui.dandiarchive.org, while the apex domain dandiarchive.org is controlled by the redirector. The redirector performs two main tasks

1. Redirect requests from dandiarchive.org to gui.dandiarchive.org
2. Serve JSON information about deployed services (e.g. urls for the API, web ui, and jupyterhub) at dandiarchive.org/server-info.

We've decided that our UI is stable enough to warrant serving it directly at dandiarchive.org, leaving just the task of serving a JSON file containing deployment information. Netlify seems capable of performing this task, and this document outlines the proposal to do so.

## Serving the Deployment JSON file

Allowing Netlify to serve this deployment info can be broken down into two sub-tasks

1. Serving the JSON file at sub path of dandiarchive.org without interfering with the GUI
2. Obtaning the statically coded JSON file at or before client build time, so that Netlify may serve it

## Serving the JSON file

This is easily accomplished with Netlify [redirects](https://docs.netlify.com/routing/redirects/). The additional code this would amount to would resemble the following

```toml
# netlify.toml

[[redirects]]
from = "/server-info"
to = "/server-info.json"
status = 200
```

## Obtaining the static JSON file

Since Netlify is merely serving content for us, we need a way to include this JSON file as a local file, either as a part of, or a prerequisite to the build process. Rather than hardcoding this file in the source code, where it must be regularly updated, the API `/api/info` endpoint could be augmented to include this information as well. The Netlify build process would then simply be updated to download this file and serve it as shown above. The fetching and downloading of this file can be done through Nelify [Build Plugins](https://docs.netlify.com/configure-builds/build-plugins/).

Build plugins contain [events](https://docs.netlify.com/configure-builds/build-plugins/create-plugins/#plug-into-events), one of which is the `onPreBuild` event. This event can be used to download the file, at which point it will be ready for serving as shown above. We'd likely want to include some kind of retry mechanism, to prevent failed requests from stopping the entire build process.


## Backwards Compatibility

To maintain backwards compatibility, old gui.dandiarchive.org URLs should be redirected to dandiarchive.org. This can be trvially achieved by updating our AWS Route53 configuration.
