# EMBER-DANDI Archive

![](https://about.dandiarchive.org/assets/dandi_logo.svg)

## EMBER: Ecosystem for Multi-modal Brain-behavior Experimentation and Research

[EMBER](https://emberarchive.org) is the BRAIN Initiative data archive for multi-modal neurophysical and behavioral data, supporting the Brain Behavior Quantification and Synchronization (BBQS) Program.

## DANDI: Distributed Archives for Neurophysiology Data Integration

[DANDI](https://dandiarchive.org/) is a platform for publishing, sharing, and processing neurophysiology data
funded by the [BRAIN Initiative](https://braininitiative.nih.gov/). The archive
accepts cellular neurophysiology data including electrophysiology,
optophysiology, and behavioral time-series, and images from immunostaining
experiments. This archive is not just an endpoint to store data, it is intended as a living repository that enables
collaboration within and across labs, as well as the entry point for research.

## Structure

The ember-dandi-archive repository contains a Django-based [backend](dandiapi/) to run the DANDI REST API, and a
Vue-based [frontend](web/) to provide a user interface to the archive.

## Resources

* To learn how to interact with the archive,
see the [DANDI Docs](https://docs.dandiarchive.org).

* To get help:
  - ask a question: https://github.com/dandi/helpdesk/discussions
  - file a feature request or bug report: https://github.com/dandi/helpdesk/issues/new/choose
  - contact the DANDI team: help@dandiarchive.org

* To understand how to hack on the archive codebase:
  - Django backend: [`DEVELOPMENT.md`](DEVELOPMENT.md)
  - Vue frontend: [`web/README.md`](web/README.md)

