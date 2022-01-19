# dandi-archive

![](https://www.dandiarchive.org/assets/dandi_logo.svg)

*DANDI: Distributed Archives for Neurophysiology Data Integration*

DANDI is a platform for publishing, sharing, and processing neurophysiology data
funded by the [BRAIN Initiative](https://braininitiative.nih.gov/). The archive
accepts cellular neurophysiology data including electrophysiology,
optophysiology, and behavioral time-series, and images from immunostaining
experiments. The platform is [now available](https://dandiarchive.org/) for data
upload and distribution. For instructions on how to interact with the archive
see [the handbook](https://www.dandiarchive.org/handbook/).

## Structure

This repository contains a Django-based backend to run the DANDI REST API, and a
Vue-based [frontend](web/) to provide a user interface to the archive.

## Resources

To get help:
- ask a question: https://github.com/dandi/helpdesk/discussions
- file a feature request or bug report: https://github.com/dandi/helpdesk/issues
- contact the DANDI team: help@dandiarchive.org

To hack on the archive codebase:
- [`DEVELOPMENT.md`](DEVELOPMENT.md)
