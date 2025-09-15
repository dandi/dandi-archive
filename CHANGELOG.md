# v0.14.0 (Mon Sep 15 2025)

#### 🚀 Enhancement

- Add admin user list endpoint [#2537](https://github.com/dandi/dandi-archive/pull/2537) ([@jjnesbitt](https://github.com/jjnesbitt))
- Fix embargoed dandiset creation form [#2462](https://github.com/dandi/dandi-archive/pull/2462) ([@bendichter](https://github.com/bendichter) [@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 3

- Ben Dichter ([@bendichter](https://github.com/bendichter))
- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.13.6 (Fri Sep 12 2025)

#### 🐛 Bug Fix

- Don't modify existing object tags when adding/removing embargoed tags [#2517](https://github.com/dandi/dandi-archive/pull/2517) ([@jjnesbitt](https://github.com/jjnesbitt))
- DOC: remove "Are you lost?" [#2530](https://github.com/dandi/dandi-archive/pull/2530) ([@yarikoptic](https://github.com/yarikoptic))

#### Authors: 2

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.13.5 (Tue Sep 09 2025)

#### 🐛 Bug Fix

- Upgrade django-resonant-settings, back out temporary fix [#2524](https://github.com/dandi/dandi-archive/pull/2524) ([@mvandenburgh](https://github.com/mvandenburgh))
- Temporarily override broken upstream setting [#2522](https://github.com/dandi/dandi-archive/pull/2522) ([@mvandenburgh](https://github.com/mvandenburgh))

#### 🏠 Internal

- Fix typo in gunicorn conf file [#2528](https://github.com/dandi/dandi-archive/pull/2528) ([@jjnesbitt](https://github.com/jjnesbitt))
- Include `gunicorn.conf.py` in heroku sdist [#2526](https://github.com/dandi/dandi-archive/pull/2526) ([@mvandenburgh](https://github.com/mvandenburgh))
- Configure `gunicorn` to include username in access logs [#2525](https://github.com/dandi/dandi-archive/pull/2525) ([@mvandenburgh](https://github.com/mvandenburgh))
- Update to Django 5 [#2419](https://github.com/dandi/dandi-archive/pull/2419) ([@mvandenburgh](https://github.com/mvandenburgh))
- Switch the default storage to always use `S3Storage` [#2500](https://github.com/dandi/dandi-archive/pull/2500) ([@brianhelba](https://github.com/brianhelba))

#### 🔩 Dependency Updates

- [gh-actions](deps): Bump actions/setup-node from 4 to 5 [#2529](https://github.com/dandi/dandi-archive/pull/2529) ([@dependabot[bot]](https://github.com/dependabot[bot]))

#### Authors: 4

- [@dependabot[bot]](https://github.com/dependabot[bot])
- Brian Helba ([@brianhelba](https://github.com/brianhelba))
- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.13.4 (Thu Aug 28 2025)

#### 🐛 Bug Fix

- Add endpoint for retrieving custom audit info [#2467](https://github.com/dandi/dandi-archive/pull/2467) ([@jjnesbitt](https://github.com/jjnesbitt))

#### Authors: 1

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))

---

# v0.13.3 (Thu Aug 28 2025)

#### 🧪 Tests

- Repoint CLI tests at master/published release [#2513](https://github.com/dandi/dandi-archive/pull/2513) ([@mvandenburgh](https://github.com/mvandenburgh))

#### 🔩 Dependency Updates

- Fix minor issues with `pyproject.toml` `dependencies` [#2519](https://github.com/dandi/dandi-archive/pull/2519) ([@brianhelba](https://github.com/brianhelba))

#### Authors: 2

- Brian Helba ([@brianhelba](https://github.com/brianhelba))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.13.2 (Wed Aug 27 2025)

#### 🐛 Bug Fix

- Apply embargo functionality to dandiset manifest files [#2516](https://github.com/dandi/dandi-archive/pull/2516) ([@jjnesbitt](https://github.com/jjnesbitt))
- Fix broken links: Terms and Policies [#2512](https://github.com/dandi/dandi-archive/pull/2512) ([@NEStock](https://github.com/NEStock))

#### 🏠 Internal

- Use allauth setting to restrict prod to github auth [#2514](https://github.com/dandi/dandi-archive/pull/2514) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 3

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Nicole Stock Tregoning ([@NEStock](https://github.com/NEStock))

---

# v0.13.1 (Tue Aug 26 2025)

#### 🏠 Internal

- Switch to `uv`, upgrade `ruff` [#2502](https://github.com/dandi/dandi-archive/pull/2502) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.13.0 (Tue Aug 26 2025)

#### 🚀 Enhancement

- Fix avatar and new dandiset button line break issue in header [#2504](https://github.com/dandi/dandi-archive/pull/2504) ([@jtomeck](https://github.com/jtomeck) [@mvandenburgh](https://github.com/mvandenburgh))

#### 🏠 Internal

- Include asset size in audit record [#2511](https://github.com/dandi/dandi-archive/pull/2511) ([@mvandenburgh](https://github.com/mvandenburgh))
- Fix Bug in collect_garbage.py with printing [#2509](https://github.com/dandi/dandi-archive/pull/2509) ([@NEStock](https://github.com/NEStock))
- Fix Dockerfile for dev django [#2505](https://github.com/dandi/dandi-archive/pull/2505) ([@jjnesbitt](https://github.com/jjnesbitt))

#### Authors: 4

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Jared Tomeck ([@jtomeck](https://github.com/jtomeck))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Nicole Stock Tregoning ([@NEStock](https://github.com/NEStock))

---

# v0.12.16 (Mon Aug 25 2025)

#### 🏠 Internal

- Add middleware/logger to log username on every request [#2451](https://github.com/dandi/dandi-archive/pull/2451) ([@mvandenburgh](https://github.com/mvandenburgh) [@jjnesbitt](https://github.com/jjnesbitt))

#### 🧪 Tests

- Revert "Temporarily point CLI tests at PR branch" [#2496](https://github.com/dandi/dandi-archive/pull/2496) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 2

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.12.15 (Fri Aug 22 2025)

#### 🏠 Internal

- Add HTTP redirect for staging server [#2449](https://github.com/dandi/dandi-archive/pull/2449) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.12.14 (Fri Aug 22 2025)

#### 🐛 Bug Fix

- Only include tagging header in zarr upload URL if zarr is embargoed [#2503](https://github.com/dandi/dandi-archive/pull/2503) ([@jjnesbitt](https://github.com/jjnesbitt))

#### 🏠 Internal

- Remove references to `DANDI_ALLOW_LOCALHOST_URLS` env var [#2499](https://github.com/dandi/dandi-archive/pull/2499) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 2

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.12.13 (Mon Aug 18 2025)

#### 🐛 Bug Fix

- Only search by etag in AssetBlob `get_or_create` [#2498](https://github.com/dandi/dandi-archive/pull/2498) ([@jjnesbitt](https://github.com/jjnesbitt))

#### 🏠 Internal

- Expect that AssetBlob.etag should be unique, regardless of size [#2478](https://github.com/dandi/dandi-archive/pull/2478) ([@brianhelba](https://github.com/brianhelba))

#### 🧪 Tests

- Test that tagging applied to zarr pre-signed PUT URLs [#2494](https://github.com/dandi/dandi-archive/pull/2494) ([@jjnesbitt](https://github.com/jjnesbitt))

#### Authors: 2

- Brian Helba ([@brianhelba](https://github.com/brianhelba))
- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))

---

# v0.12.12 (Mon Aug 18 2025)

#### 🐛 Bug Fix

- Empty commit to trigger a release [#2495](https://github.com/dandi/dandi-archive/pull/2495) ([@mvandenburgh](https://github.com/mvandenburgh))

#### 🏠 Internal

- Switch `django-composed-configuration` to flat settings [#2483](https://github.com/dandi/dandi-archive/pull/2483) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.12.11 (Thu Aug 14 2025)

#### 🐛 Bug Fix

- Empty commit to trigger a release [#2492](https://github.com/dandi/dandi-archive/pull/2492) ([@mvandenburgh](https://github.com/mvandenburgh))
- Revert change to github token again [#2491](https://github.com/dandi/dandi-archive/pull/2491) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.12.10 (Thu Aug 14 2025)

#### 🐛 Bug Fix

- Revert change to github token [#2490](https://github.com/dandi/dandi-archive/pull/2490) ([@mvandenburgh](https://github.com/mvandenburgh))
- Support embargo tags in generated zarr upload URLs [#2489](https://github.com/dandi/dandi-archive/pull/2489) ([@jjnesbitt](https://github.com/jjnesbitt))

#### 🏠 Internal

- Improvements to GitHub Actions [#2465](https://github.com/dandi/dandi-archive/pull/2465) ([@mvandenburgh](https://github.com/mvandenburgh))
- Fix "union-attr" type errors [#2476](https://github.com/dandi/dandi-archive/pull/2476) ([@brianhelba](https://github.com/brianhelba))
- Fix AnonymousUser-related type errors [#2477](https://github.com/dandi/dandi-archive/pull/2477) ([@brianhelba](https://github.com/brianhelba))

#### 🔩 Dependency Updates

- [gh-actions](deps): Bump actions/download-artifact from 4 to 5 [#2482](https://github.com/dandi/dandi-archive/pull/2482) ([@dependabot[bot]](https://github.com/dependabot[bot]))
- [gh-actions](deps): Bump actions/checkout from 4 to 5 [#2481](https://github.com/dandi/dandi-archive/pull/2481) ([@dependabot[bot]](https://github.com/dependabot[bot]))

#### Authors: 4

- [@dependabot[bot]](https://github.com/dependabot[bot])
- Brian Helba ([@brianhelba](https://github.com/brianhelba))
- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.12.9 (Mon Aug 11 2025)

#### 🐛 Bug Fix

- Add support to open NIfTI-Zarr assets with the OME-Zarr Validator external service [#2455](https://github.com/dandi/dandi-archive/pull/2455) ([@kabilar](https://github.com/kabilar))

#### 🔩 Dependency Updates

- Remove `s3-log-parse` dependency [#2480](https://github.com/dandi/dandi-archive/pull/2480) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 2

- Kabilar Gunalan ([@kabilar](https://github.com/kabilar))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.12.8 (Mon Aug 11 2025)

#### 🐛 Bug Fix

- Extend allowed time to fulfill PUT upload to half-hour from 10 minutes [#2456](https://github.com/dandi/dandi-archive/pull/2456) ([@yarikoptic](https://github.com/yarikoptic) [@jjnesbitt](https://github.com/jjnesbitt))

#### 🏎 Performance

- Use asset paths for dandiset list size order subquery [#2479](https://github.com/dandi/dandi-archive/pull/2479) ([@jjnesbitt](https://github.com/jjnesbitt))

#### 🏠 Internal

- Remove unused code [#2475](https://github.com/dandi/dandi-archive/pull/2475) ([@mvandenburgh](https://github.com/mvandenburgh))

#### 📝 Documentation

- Improve and update doc regarding the `psycopg` dependency and its system dependencies [#2406](https://github.com/dandi/dandi-archive/pull/2406) ([@candleindark](https://github.com/candleindark) [@jjnesbitt](https://github.com/jjnesbitt))

#### Authors: 4

- Isaac To ([@candleindark](https://github.com/candleindark))
- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.12.7 (Thu Aug 07 2025)

#### 🐛 Bug Fix

- Fix broken behavior when text includes single quotes [#2474](https://github.com/dandi/dandi-archive/pull/2474) ([@jjnesbitt](https://github.com/jjnesbitt))

#### Authors: 1

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))

---

# v0.12.6 (Thu Aug 07 2025)

#### 🐛 Bug Fix

- Retain focus on meditor text input fields [#2471](https://github.com/dandi/dandi-archive/pull/2471) ([@jjnesbitt](https://github.com/jjnesbitt))
- Declare  the same minimal version of dandi-cli as we announce in /info (/server-info) [#2458](https://github.com/dandi/dandi-archive/pull/2458) ([@yarikoptic](https://github.com/yarikoptic))

#### 🏠 Internal

- Miscellaneous improvements [#2468](https://github.com/dandi/dandi-archive/pull/2468) ([@mvandenburgh](https://github.com/mvandenburgh))
- Include other files needed by Heroku in sdist [#2472](https://github.com/dandi/dandi-archive/pull/2472) ([@mvandenburgh](https://github.com/mvandenburgh))
- Ensure `requirements.txt` is included in sdist [#2470](https://github.com/dandi/dandi-archive/pull/2470) ([@mvandenburgh](https://github.com/mvandenburgh))
- Add `requirements.txt` [#2469](https://github.com/dandi/dandi-archive/pull/2469) ([@mvandenburgh](https://github.com/mvandenburgh))
- Switch from setuptools to hatchling [#2466](https://github.com/dandi/dandi-archive/pull/2466) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 3

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.12.5 (Tue Aug 05 2025)

#### 🐛 Bug Fix

- DLP Sidebar Design [#2452](https://github.com/dandi/dandi-archive/pull/2452) ([@jtomeck](https://github.com/jtomeck) [@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 2

- Jared Tomeck ([@jtomeck](https://github.com/jtomeck))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.12.4 (Wed Jul 30 2025)

#### 🐛 Bug Fix

- Fix metadata alignment and spacing [#2454](https://github.com/dandi/dandi-archive/pull/2454) ([@jtomeck](https://github.com/jtomeck) [@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 2

- Jared Tomeck ([@jtomeck](https://github.com/jtomeck))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.12.3 (Wed Jul 30 2025)

#### 🐛 Bug Fix

- Fix spacing of DLP cards on left side of page [#2453](https://github.com/dandi/dandi-archive/pull/2453) ([@jtomeck](https://github.com/jtomeck) [@mvandenburgh](https://github.com/mvandenburgh))

#### 📝 Documentation

- doc: dev setup and execution of e2e web tests [#2411](https://github.com/dandi/dandi-archive/pull/2411) ([@asmacdo](https://github.com/asmacdo))

#### Authors: 3

- Austin Macdonald ([@asmacdo](https://github.com/asmacdo))
- Jared Tomeck ([@jtomeck](https://github.com/jtomeck))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.12.2 (Tue Jul 22 2025)

#### 🏠 Internal

- Point staging web app at sandbox URL [#2446](https://github.com/dandi/dandi-archive/pull/2446) ([@mvandenburgh](https://github.com/mvandenburgh))
- Add source script for fish shell [#2440](https://github.com/dandi/dandi-archive/pull/2440) ([@jjnesbitt](https://github.com/jjnesbitt))

#### Authors: 2

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.12.1 (Fri Jul 18 2025)

#### 🐛 Bug Fix

- Update hardcoded staging URL [#2441](https://github.com/dandi/dandi-archive/pull/2441) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.12.0 (Fri Jul 18 2025)

#### 🚀 Enhancement

- Redirect `gui-staging` URLs to `sandbox` [#2439](https://github.com/dandi/dandi-archive/pull/2439) ([@mvandenburgh](https://github.com/mvandenburgh))

#### 🐛 Bug Fix

- ENH: add filtering capabilities to NestedAssetViewSet [#2414](https://github.com/dandi/dandi-archive/pull/2414) ([@bendichter](https://github.com/bendichter))

#### 📝 Documentation

- Use 1. for all items in markdown ordered lists [#2436](https://github.com/dandi/dandi-archive/pull/2436) ([@jjnesbitt](https://github.com/jjnesbitt))

#### Authors: 3

- Ben Dichter ([@bendichter](https://github.com/bendichter))
- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.11.9 (Mon Jul 14 2025)

#### 🏎 Performance

- Replace stats endpoint caching with ApplicationStats model [#2435](https://github.com/dandi/dandi-archive/pull/2435) ([@jjnesbitt](https://github.com/jjnesbitt))

#### 🏠 Internal

- Remove the rest of `dandiapi.analytics` [#2438](https://github.com/dandi/dandi-archive/pull/2438) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 2

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.11.8 (Fri Jul 11 2025)

#### 🐛 Bug Fix

- Remove `ProcessedS3Log` model [#2426](https://github.com/dandi/dandi-archive/pull/2426) ([@mvandenburgh](https://github.com/mvandenburgh))
- Fix type checking error [#2437](https://github.com/dandi/dandi-archive/pull/2437) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.11.7 (Fri Jul 11 2025)

#### 🐛 Bug Fix

- Fix Meditor rendering bugs [#2434](https://github.com/dandi/dandi-archive/pull/2434) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.11.6 (Thu Jul 10 2025)

#### 🐛 Bug Fix

- Fix missing species on search page [#2422](https://github.com/dandi/dandi-archive/pull/2422) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.11.5 (Thu Jul 03 2025)

#### 🐛 Bug Fix

- Remove s3 log processing task [#2425](https://github.com/dandi/dandi-archive/pull/2425) ([@mvandenburgh](https://github.com/mvandenburgh))
- enh: add action to export github usernames [#2424](https://github.com/dandi/dandi-archive/pull/2424) ([@satra](https://github.com/satra) [@jjnesbitt](https://github.com/jjnesbitt))

#### 🏎 Performance

- Set `statement_timeout` in materialized view query [#2427](https://github.com/dandi/dandi-archive/pull/2427) ([@mvandenburgh](https://github.com/mvandenburgh))

#### 🔩 Dependency Updates

- Update to Python 3.13 [#2420](https://github.com/dandi/dandi-archive/pull/2420) ([@mvandenburgh](https://github.com/mvandenburgh) [@waxlamp](https://github.com/waxlamp))

#### Authors: 4

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))
- Satrajit Ghosh ([@satra](https://github.com/satra))

---

# v0.11.4 (Tue Jul 01 2025)

#### 🐛 Bug Fix

- Set timeout of refresh_materialized_view_search to 10 minutes [#2423](https://github.com/dandi/dandi-archive/pull/2423) ([@jjnesbitt](https://github.com/jjnesbitt))

#### Authors: 1

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))

---

# v0.11.3 (Mon Jun 30 2025)

#### 🐛 Bug Fix

- Increase timeout for `refresh_materialized_view_search` [#2421](https://github.com/dandi/dandi-archive/pull/2421) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.11.2 (Mon Jun 23 2025)

#### 🐛 Bug Fix

- Empty commit to force release cycle [#2418](https://github.com/dandi/dandi-archive/pull/2418) ([@waxlamp](https://github.com/waxlamp))
- ENH: allow googlebot also /search endpoint and for filtered listing of assets [#2408](https://github.com/dandi/dandi-archive/pull/2408) ([@yarikoptic](https://github.com/yarikoptic))

#### 🏠 Internal

- Remove gossip and mingling from Celery workers [#2251](https://github.com/dandi/dandi-archive/pull/2251) (aaronkanzer@dhcp-10-29-159-71.dyn.mit.edu [@aaronkanzer](https://github.com/aaronkanzer))

#### Authors: 4

- [@aaronkanzer](https://github.com/aaronkanzer)
- Aaron Kanzer (aaronkanzer@dhcp-10-29-159-71.dyn.mit.edu)
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.11.1 (Thu Jun 05 2025)

#### 🏎 Performance

- fix: update robots.txt rules to disallow specific asset API endpoints for Googlebot [#2401](https://github.com/dandi/dandi-archive/pull/2401) ([@bendichter](https://github.com/bendichter))
- Including trailing slash on assets frontend call to prevent redundancy [#2402](https://github.com/dandi/dandi-archive/pull/2402) (aaronkanzer@dhcp-10-29-186-193.dyn.MIT.EDU [@aaronkanzer](https://github.com/aaronkanzer))

#### 🏠 Internal

- Prune web/ from sdist of dandiarchive/ and thus when uploading to heroku [#2403](https://github.com/dandi/dandi-archive/pull/2403) ([@yarikoptic](https://github.com/yarikoptic))

#### 📝 Documentation

- Add staging rename design doc [#2229](https://github.com/dandi/dandi-archive/pull/2229) ([@waxlamp](https://github.com/waxlamp))
- Design document for the Zenodo like DOI per dandiset [#2012](https://github.com/dandi/dandi-archive/pull/2012) ([@yarikoptic](https://github.com/yarikoptic) [@asmacdo](https://github.com/asmacdo))
- Give explicit instructions on where to get code and check/set port for django DB [#2400](https://github.com/dandi/dandi-archive/pull/2400) ([@yarikoptic](https://github.com/yarikoptic))

#### Authors: 6

- [@aaronkanzer](https://github.com/aaronkanzer)
- Aaron Kanzer (aaronkanzer@dhcp-10-29-186-193.dyn.MIT.EDU)
- Austin Macdonald ([@asmacdo](https://github.com/asmacdo))
- Ben Dichter ([@bendichter](https://github.com/bendichter))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.11.0 (Wed Jun 04 2025)

:tada: This release contains work from a new contributor! :tada:

Thank you, Nicole Stock Tregoning ([@NEStock](https://github.com/NEStock)), for all your work!

#### 🚀 Enhancement

- Bump dandischema to 0.11.1 in API dependencies; bring back "yarn migrate" command to update typings for frontend/schema [#2383](https://github.com/dandi/dandi-archive/pull/2383) (aaronkanzer@Aarons-MacBook-Pro-2.local [@yarikoptic](https://github.com/yarikoptic) [@aaronkanzer](https://github.com/aaronkanzer))

#### 🐛 Bug Fix

- fix: update backend (API) robots.txt to allow Googlebot access to dandiset metadata [#2397](https://github.com/dandi/dandi-archive/pull/2397) ([@bendichter](https://github.com/bendichter) [@yarikoptic](https://github.com/yarikoptic))
- fix: update pytest version constraints for compat with factoryboy ([@bendichter](https://github.com/bendichter))
- Fix broken/out-of-date docs links [#2371](https://github.com/dandi/dandi-archive/pull/2371) ([@NEStock](https://github.com/NEStock))
- Fix formatting of approved user message template [#2373](https://github.com/dandi/dandi-archive/pull/2373) ([@kabilar](https://github.com/kabilar))

#### 🧪 Tests

- Fix Frontend CI Failing: remove " " from the Sign In/Up button names [#2389](https://github.com/dandi/dandi-archive/pull/2389) ([@NEStock](https://github.com/NEStock))

#### Authors: 6

- [@aaronkanzer](https://github.com/aaronkanzer)
- Aaron Kanzer (aaronkanzer@Aarons-MacBook-Pro-2.local)
- Ben Dichter ([@bendichter](https://github.com/bendichter))
- Kabilar Gunalan ([@kabilar](https://github.com/kabilar))
- Nicole Stock Tregoning ([@NEStock](https://github.com/NEStock))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.10.0 (Wed Apr 30 2025)

#### 🚀 Enhancement

- Remove margin around DandisetList [#2366](https://github.com/dandi/dandi-archive/pull/2366) ([@naglepuff](https://github.com/naglepuff))

#### Authors: 1

- Michael Nagler ([@naglepuff](https://github.com/naglepuff))

---

# v0.9.0 (Wed Apr 30 2025)

#### 🚀 Enhancement

- Fix display of dandisets with many owners [#2272](https://github.com/dandi/dandi-archive/pull/2272) ([@bendichter](https://github.com/bendichter) [@jjnesbitt](https://github.com/jjnesbitt))
- Update sorting controls for Dandisets page [#2358](https://github.com/dandi/dandi-archive/pull/2358) ([@naglepuff](https://github.com/naglepuff))
- Auto-allow people with `@nih.gov` and `@janelia.hhmi.org` email addresses [#2340](https://github.com/dandi/dandi-archive/pull/2340) ([@kabilar](https://github.com/kabilar) [@waxlamp](https://github.com/waxlamp))

#### 🐛 Bug Fix

- Check to see if cookies are enabled for banner message [#2359](https://github.com/dandi/dandi-archive/pull/2359) ([@naglepuff](https://github.com/naglepuff))
- Revert "Convert StagingApplication to a proxy model" [#2357](https://github.com/dandi/dandi-archive/pull/2357) ([@jjnesbitt](https://github.com/jjnesbitt))
- Convert StagingApplication to a proxy model [#2339](https://github.com/dandi/dandi-archive/pull/2339) ([@jjnesbitt](https://github.com/jjnesbitt))

#### 🏠 Internal

- Make eslint fail on warning [#2360](https://github.com/dandi/dandi-archive/pull/2360) ([@mvandenburgh](https://github.com/mvandenburgh))

#### 📝 Documentation

- Remove import_dandisets command from docs [#2351](https://github.com/dandi/dandi-archive/pull/2351) ([@asmacdo](https://github.com/asmacdo))

#### 🧪 Tests

- Parametrize e2e tests in CI to run in both prod/dev modes [#2361](https://github.com/dandi/dandi-archive/pull/2361) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 7

- Austin Macdonald ([@asmacdo](https://github.com/asmacdo))
- Ben Dichter ([@bendichter](https://github.com/bendichter))
- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Kabilar Gunalan ([@kabilar](https://github.com/kabilar))
- Michael Nagler ([@naglepuff](https://github.com/naglepuff))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))

---

# v0.8.1 (Mon Apr 21 2025)

#### 🏠 Internal

- Integrate `garbage_collection` service into `collect_garbage.py` [#2343](https://github.com/dandi/dandi-archive/pull/2343) ([@mvandenburgh](https://github.com/mvandenburgh))

#### 🧪 Tests

- Remove unneeded data from playwright test fixture [#2341](https://github.com/dandi/dandi-archive/pull/2341) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.8.0 (Fri Apr 18 2025)

#### 🚀 Enhancement

- Move banner with info blurb to top of all pages [#2329](https://github.com/dandi/dandi-archive/pull/2329) ([@naglepuff](https://github.com/naglepuff))

#### 🐛 Bug Fix

- Don't override oauth2_provider settings dict [#2337](https://github.com/dandi/dandi-archive/pull/2337) ([@mvandenburgh](https://github.com/mvandenburgh))
- Fix oauth2 setting [#2335](https://github.com/dandi/dandi-archive/pull/2335) ([@mvandenburgh](https://github.com/mvandenburgh))
- Require minimum version of 2.0 for django-oauth-toolkit [#2326](https://github.com/dandi/dandi-archive/pull/2326) ([@jjnesbitt](https://github.com/jjnesbitt))

#### 🏠 Internal

- Revert OAuth model change [#2338](https://github.com/dandi/dandi-archive/pull/2338) ([@mvandenburgh](https://github.com/mvandenburgh))
- Switch from `runtime.txt` to `.python-version` [#2332](https://github.com/dandi/dandi-archive/pull/2332) ([@mvandenburgh](https://github.com/mvandenburgh))
- Switch staging back to builtin oauth `Application` [#2331](https://github.com/dandi/dandi-archive/pull/2331) ([@mvandenburgh](https://github.com/mvandenburgh))
- Update swagger/redocs urls to align with Resonant [#2327](https://github.com/dandi/dandi-archive/pull/2327) ([@mvandenburgh](https://github.com/mvandenburgh))

#### 📝 Documentation

- DOC: fixup description of the interaction with auto for releases based on labels [#2285](https://github.com/dandi/dandi-archive/pull/2285) ([@yarikoptic](https://github.com/yarikoptic) [@waxlamp](https://github.com/waxlamp))

#### 🔩 Dependency Updates

- Clean up `setup.py` [#2324](https://github.com/dandi/dandi-archive/pull/2324) ([@mvandenburgh](https://github.com/mvandenburgh))
- Update Heroku Python runtime [#2323](https://github.com/dandi/dandi-archive/pull/2323) ([@mvandenburgh](https://github.com/mvandenburgh))
- Unpin `django-oauth-toolkit`, generate migrations for downstream `StagingApplication` [#2320](https://github.com/dandi/dandi-archive/pull/2320) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 5

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Michael Nagler ([@naglepuff](https://github.com/naglepuff))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.7.0 (Wed Apr 16 2025)

#### 🚀 Enhancement

- Add warning alert for test dandisets in CreateDandisetView [#2283](https://github.com/dandi/dandi-archive/pull/2283) ([@bendichter](https://github.com/bendichter))

#### Authors: 1

- Ben Dichter ([@bendichter](https://github.com/bendichter))

---

# v0.6.0 (Wed Apr 16 2025)

#### 🚀 Enhancement

- Conditionally display sticky banner [#2321](https://github.com/dandi/dandi-archive/pull/2321) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.5.0 (Wed Apr 16 2025)

:tada: This release contains work from a new contributor! :tada:

Thank you, Michael Nagler ([@naglepuff](https://github.com/naglepuff)), for all your work!

#### 🚀 Enhancement

- Display the number of results found in DandisetSearchField [#2293](https://github.com/dandi/dandi-archive/pull/2293) ([@bendichter](https://github.com/bendichter))
- Metadata correction [#2177](https://github.com/dandi/dandi-archive/pull/2177) ([@candleindark](https://github.com/candleindark) [@jjnesbitt](https://github.com/jjnesbitt))
- Allow null `user` when `admin` is True [#2242](https://github.com/dandi/dandi-archive/pull/2242) ([@waxlamp](https://github.com/waxlamp))
- Add admin and description fields to AuditRecord model [#2225](https://github.com/dandi/dandi-archive/pull/2225) ([@jjnesbitt](https://github.com/jjnesbitt))
- Vue 3 Migration feature branch [#2186](https://github.com/dandi/dandi-archive/pull/2186) ([@mvandenburgh](https://github.com/mvandenburgh))

#### 🐛 Bug Fix

- Fix validation issue with vue/vjsf 3 [#2317](https://github.com/dandi/dandi-archive/pull/2317) ([@mvandenburgh](https://github.com/mvandenburgh))
- Remove console.log invocation [#2318](https://github.com/dandi/dandi-archive/pull/2318) ([@mvandenburgh](https://github.com/mvandenburgh))
- Remove hardcoded string for pending status [#2315](https://github.com/dandi/dandi-archive/pull/2315) ([@danlamanna](https://github.com/danlamanna))
- Add default ordering for uploads [#2309](https://github.com/dandi/dandi-archive/pull/2309) ([@danlamanna](https://github.com/danlamanna))
- Fix invalid closing li tag [#2304](https://github.com/dandi/dandi-archive/pull/2304) ([@danlamanna](https://github.com/danlamanna))
- Show empty dandisets for search by default [#2291](https://github.com/dandi/dandi-archive/pull/2291) ([@naglepuff](https://github.com/naglepuff))
- Lock dandiset when changing owners [#2288](https://github.com/dandi/dandi-archive/pull/2288) ([@naglepuff](https://github.com/naglepuff))
- Refactor StarButton layout and improve alignment in DandisetMain view [#2282](https://github.com/dandi/dandi-archive/pull/2282) ([@bendichter](https://github.com/bendichter))
- Fix a case where draft asset summaries could become stale [#2231](https://github.com/dandi/dandi-archive/pull/2231) ([@danlamanna](https://github.com/danlamanna))
- Fix v-switch margins and color [#2290](https://github.com/dandi/dandi-archive/pull/2290) ([@mvandenburgh](https://github.com/mvandenburgh))
- Use `placeholder` instead of `label` for dandiset search bar [#2287](https://github.com/dandi/dandi-archive/pull/2287) ([@mvandenburgh](https://github.com/mvandenburgh))
- Fix cutoff text on CopyText form [#2286](https://github.com/dandi/dandi-archive/pull/2286) ([@mvandenburgh](https://github.com/mvandenburgh))
- Add padding to stop meditor icon from getting cut off [#2278](https://github.com/dandi/dandi-archive/pull/2278) ([@mvandenburgh](https://github.com/mvandenburgh))
- Fix position of Manage Owners button [#2279](https://github.com/dandi/dandi-archive/pull/2279) ([@mvandenburgh](https://github.com/mvandenburgh))
- Fix star button disabled halo issue [#2276](https://github.com/dandi/dandi-archive/pull/2276) ([@mvandenburgh](https://github.com/mvandenburgh))
- Fix alignment issue with Manage Owners button [#2277](https://github.com/dandi/dandi-archive/pull/2277) ([@mvandenburgh](https://github.com/mvandenburgh))
- Fix z-index of cookie banner [#2265](https://github.com/dandi/dandi-archive/pull/2265) ([@mvandenburgh](https://github.com/mvandenburgh))
- Fix "View asset metadata" link [#2260](https://github.com/dandi/dandi-archive/pull/2260) ([@mvandenburgh](https://github.com/mvandenburgh))
- Fix Share icon size [#2264](https://github.com/dandi/dandi-archive/pull/2264) ([@mvandenburgh](https://github.com/mvandenburgh))
- Fix link dropdown text on mobile [#2266](https://github.com/dandi/dandi-archive/pull/2266) ([@mvandenburgh](https://github.com/mvandenburgh))
- Compute zarr checksums outside of transactions [#2267](https://github.com/dandi/dandi-archive/pull/2267) ([@danlamanna](https://github.com/danlamanna))
- Add Sentry back to Vue application [#2258](https://github.com/dandi/dandi-archive/pull/2258) ([@mvandenburgh](https://github.com/mvandenburgh))
- Don't suppress exceptions when fetching schema/logging in [#2257](https://github.com/dandi/dandi-archive/pull/2257) ([@mvandenburgh](https://github.com/mvandenburgh))
- Remove quotes on DANDI_ADMIN_EMAIL env var [#2226](https://github.com/dandi/dandi-archive/pull/2226) ([@jjnesbitt](https://github.com/jjnesbitt))
- Add version string back into frontend [#2236](https://github.com/dandi/dandi-archive/pull/2236) ([@mvandenburgh](https://github.com/mvandenburgh))

#### 🏎 Performance

- Remove n+1 queries from Asset.full_metadata [#2316](https://github.com/dandi/dandi-archive/pull/2316) ([@danlamanna](https://github.com/danlamanna))
- Denormalize species for faster searching [#2308](https://github.com/dandi/dandi-archive/pull/2308) ([@danlamanna](https://github.com/danlamanna))
- Mock GC event chunk size during testing [#2313](https://github.com/dandi/dandi-archive/pull/2313) ([@danlamanna](https://github.com/danlamanna))
- Add an index for looking up pending assets [#2303](https://github.com/dandi/dandi-archive/pull/2303) ([@danlamanna](https://github.com/danlamanna))
- Optimize dandiset list query when excluding empty [#2310](https://github.com/dandi/dandi-archive/pull/2310) ([@jjnesbitt](https://github.com/jjnesbitt))

#### 🏠 Internal

- Move Asset.Status to top level AssetStatus class [#2305](https://github.com/dandi/dandi-archive/pull/2305) ([@danlamanna](https://github.com/danlamanna))
- Add required annotations import [#2312](https://github.com/dandi/dandi-archive/pull/2312) ([@danlamanna](https://github.com/danlamanna))
- Remove deprecated version field from docker compose .yml [#2307](https://github.com/dandi/dandi-archive/pull/2307) ([@mvandenburgh](https://github.com/mvandenburgh))
- Add `celerybeat-schedule*` files to .gitignore [#2280](https://github.com/dandi/dandi-archive/pull/2280) ([@mvandenburgh](https://github.com/mvandenburgh))
- update test doi server [#2241](https://github.com/dandi/dandi-archive/pull/2241) ([@satra](https://github.com/satra))
- Add Netlify configuration for branch deploys [#2228](https://github.com/dandi/dandi-archive/pull/2228) ([@waxlamp](https://github.com/waxlamp))
- Convert remaining Vue components to `<script setup>` syntax [#2238](https://github.com/dandi/dandi-archive/pull/2238) ([@mvandenburgh](https://github.com/mvandenburgh))

#### 📝 Documentation

- Update CODE_OF_CONDUCT.md [#2259](https://github.com/dandi/dandi-archive/pull/2259) ([@satra](https://github.com/satra))

#### 🧪 Tests

- Migrate puppeteer tests to playwright [#2223](https://github.com/dandi/dandi-archive/pull/2223) ([@naglepuff](https://github.com/naglepuff))

#### Authors: 8

- Ben Dichter ([@bendichter](https://github.com/bendichter))
- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Isaac To ([@candleindark](https://github.com/candleindark))
- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Michael Nagler ([@naglepuff](https://github.com/naglepuff))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))
- Satrajit Ghosh ([@satra](https://github.com/satra))

---

# v0.4.29 (Fri Mar 21 2025)

#### 🐛 Bug Fix

- enh: inject datacite metadata as schema.org for dataset search [#2212](https://github.com/dandi/dandi-archive/pull/2212) ([@satra](https://github.com/satra) [@mvandenburgh](https://github.com/mvandenburgh) [@waxlamp](https://github.com/waxlamp))

#### Authors: 3

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))
- Satrajit Ghosh ([@satra](https://github.com/satra))

---

# v0.4.28 (Mon Mar 17 2025)

#### 🐛 Bug Fix

- Allow robots on web frontend [#2200](https://github.com/dandi/dandi-archive/pull/2200) ([@yarikoptic](https://github.com/yarikoptic))

#### Authors: 1

- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.4.27 (Fri Mar 14 2025)

#### 🐛 Bug Fix

- Add search query parameter to dandiset list endpoint serializer [#2216](https://github.com/dandi/dandi-archive/pull/2216) ([@waxlamp](https://github.com/waxlamp))

#### Authors: 1

- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))

---

# v0.4.26 (Fri Mar 14 2025)

#### 🐛 Bug Fix

- Fix DANDI Docs links [#2213](https://github.com/dandi/dandi-archive/pull/2213) ([@kabilar](https://github.com/kabilar))

#### Authors: 1

- Kabilar Gunalan ([@kabilar](https://github.com/kabilar))

---

# v0.4.25 (Thu Mar 13 2025)

:tada: This release contains work from a new contributor! :tada:

Thank you, Austin Macdonald ([@asmacdo](https://github.com/asmacdo)), for all your work!

#### 🐛 Bug Fix

- Fix lingering issues with embargoed zarr implementation [#2211](https://github.com/dandi/dandi-archive/pull/2211) ([@jjnesbitt](https://github.com/jjnesbitt))
- fixup: Add admin email to CI env vars [#2205](https://github.com/dandi/dandi-archive/pull/2205) ([@asmacdo](https://github.com/asmacdo))
- Move admin email into Django setting [#2205](https://github.com/dandi/dandi-archive/pull/2205) ([@asmacdo](https://github.com/asmacdo))

#### Authors: 2

- Austin Macdonald ([@asmacdo](https://github.com/asmacdo))
- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))

---

# v0.4.24 (Thu Mar 06 2025)

#### 🐛 Bug Fix

- Return full metadata in atpath asset resource [#2204](https://github.com/dandi/dandi-archive/pull/2204) ([@jjnesbitt](https://github.com/jjnesbitt))

#### Authors: 1

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))

---

# v0.4.23 (Thu Mar 06 2025)

#### 🐛 Bug Fix

- Add trailing slash to atpath endpoint URL [#2202](https://github.com/dandi/dandi-archive/pull/2202) ([@jjnesbitt](https://github.com/jjnesbitt))

#### Authors: 1

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))

---

# v0.4.22 (Thu Mar 06 2025)

#### 🐛 Bug Fix

- Update `atpath` endpoint implementation [#2198](https://github.com/dandi/dandi-archive/pull/2198) ([@jjnesbitt](https://github.com/jjnesbitt))

#### Authors: 1

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))

---

# v0.4.21 (Wed Mar 05 2025)

#### 🐛 Bug Fix

- Implement "atpath" asset endpoint [#2193](https://github.com/dandi/dandi-archive/pull/2193) ([@jjnesbitt](https://github.com/jjnesbitt))
- Set default values for optional DandiError fields [#2192](https://github.com/dandi/dandi-archive/pull/2192) ([@jjnesbitt](https://github.com/jjnesbitt))

#### Authors: 1

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))

---

# v0.4.20 (Thu Feb 27 2025)

#### 🐛 Bug Fix

- Adjust Neurosift external URLs for v2 of Neurosift [#2189](https://github.com/dandi/dandi-archive/pull/2189) ([@magland](https://github.com/magland))

#### Authors: 1

- Jeremy Magland ([@magland](https://github.com/magland))

---

# v0.4.19 (Wed Feb 19 2025)

#### 🐛 Bug Fix

- Boost us back to 2025 in the footer after having it lost during merge conflict resolving [#2183](https://github.com/dandi/dandi-archive/pull/2183) ([@yarikoptic](https://github.com/yarikoptic))

#### Authors: 1

- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.4.18 (Fri Feb 07 2025)

#### 🐛 Bug Fix

- Fix dandiset ordering icons, default to descending [#2175](https://github.com/dandi/dandi-archive/pull/2175) ([@jjnesbitt](https://github.com/jjnesbitt))
- Add .git-blame-ignore-revs to improve blame view [#2173](https://github.com/dandi/dandi-archive/pull/2173) ([@danlamanna](https://github.com/danlamanna))

#### Authors: 2

- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))

---

# v0.4.17 (Wed Feb 05 2025)

#### 🐛 Bug Fix

- Check if dandiset contains zarr assets using asset list endpoint [#2170](https://github.com/dandi/dandi-archive/pull/2170) ([@jjnesbitt](https://github.com/jjnesbitt))

#### Authors: 1

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))

---

# v0.4.16 (Wed Feb 05 2025)

#### 🐛 Bug Fix

- Add Dandiset star functionality with UI components [#2123](https://github.com/dandi/dandi-archive/pull/2123) ([@bendichter](https://github.com/bendichter) [@jjnesbitt](https://github.com/jjnesbitt))
- Design document for "atpath" endpoint [#2155](https://github.com/dandi/dandi-archive/pull/2155) ([@jwodder](https://github.com/jwodder))

#### Authors: 3

- Ben Dichter ([@bendichter](https://github.com/bendichter))
- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- John T. Wodder II ([@jwodder](https://github.com/jwodder))

---

# v0.4.15 (Mon Feb 03 2025)

#### 🐛 Bug Fix

- Update support links in the footer [#2134](https://github.com/dandi/dandi-archive/pull/2134) ([@kabilar](https://github.com/kabilar) [@waxlamp](https://github.com/waxlamp))
- Update code of conduct contact information [#2157](https://github.com/dandi/dandi-archive/pull/2157) ([@kabilar](https://github.com/kabilar))

#### Authors: 2

- Kabilar Gunalan ([@kabilar](https://github.com/kabilar))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))

---

# v0.4.14 (Tue Jan 28 2025)

#### 🐛 Bug Fix

- Use `Unaccent` with dandiset search filter [#2142](https://github.com/dandi/dandi-archive/pull/2142) ([@jjnesbitt](https://github.com/jjnesbitt))
- `Upload` and `AssetBlob` garbage collection implementation [#2087](https://github.com/dandi/dandi-archive/pull/2087) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 2

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.4.13 (Thu Jan 23 2025)

#### 🐛 Bug Fix

- Empty commit to trigger a release [#2152](https://github.com/dandi/dandi-archive/pull/2152) ([@waxlamp](https://github.com/waxlamp))
- Add `/handbook` redirect to `docs.dandiarchive.org` [#2151](https://github.com/dandi/dandi-archive/pull/2151) ([@kabilar](https://github.com/kabilar) [@waxlamp](https://github.com/waxlamp))

#### Authors: 2

- Kabilar Gunalan ([@kabilar](https://github.com/kabilar))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))

---

# v0.4.12 (Wed Jan 22 2025)

#### 🐛 Bug Fix

- Move Google analytics tag to environment variable to prevent DANDI clones using by accident [#2126](https://github.com/dandi/dandi-archive/pull/2126) (aaronkanzer@dhcp-10-31-181-194.dyn.MIT.EDU [@aaronkanzer](https://github.com/aaronkanzer))

#### Authors: 2

- [@aaronkanzer](https://github.com/aaronkanzer)
- Aaron Kanzer (aaronkanzer@dhcp-10-31-181-194.dyn.MIT.EDU)

---

# v0.4.11 (Wed Jan 22 2025)

#### 🐛 Bug Fix

- Upgrade `dandischema` version to 0.11.0 [#2132](https://github.com/dandi/dandi-archive/pull/2132) ([@kabilar](https://github.com/kabilar))
- Add Netlify link to footer [#2133](https://github.com/dandi/dandi-archive/pull/2133) ([@kabilar](https://github.com/kabilar))
- Add Terms, Policies, and Code of Conduct to footer [#2135](https://github.com/dandi/dandi-archive/pull/2135) ([@kabilar](https://github.com/kabilar) [@waxlamp](https://github.com/waxlamp))
- Add Code of Conduct [#2130](https://github.com/dandi/dandi-archive/pull/2130) ([@kabilar](https://github.com/kabilar) [@waxlamp](https://github.com/waxlamp))

#### Authors: 2

- Kabilar Gunalan ([@kabilar](https://github.com/kabilar))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))

---

# v0.4.10 (Wed Jan 22 2025)

#### 🐛 Bug Fix

- Update URL for DANDI Docs [#2137](https://github.com/dandi/dandi-archive/pull/2137) ([@kabilar](https://github.com/kabilar) [@waxlamp](https://github.com/waxlamp))

#### Authors: 2

- Kabilar Gunalan ([@kabilar](https://github.com/kabilar))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))

---

# v0.4.9 (Wed Jan 22 2025)

#### 🐛 Bug Fix

- Update URL for DANDI About site [#2138](https://github.com/dandi/dandi-archive/pull/2138) ([@kabilar](https://github.com/kabilar))

#### Authors: 1

- Kabilar Gunalan ([@kabilar](https://github.com/kabilar))

---

# v0.4.8 (Tue Jan 21 2025)

#### 🐛 Bug Fix

- Move to 2025 from 2024 in the footer [#2144](https://github.com/dandi/dandi-archive/pull/2144) ([@yarikoptic](https://github.com/yarikoptic))

#### Authors: 1

- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.4.7 (Wed Jan 08 2025)

#### 🐛 Bug Fix

- Prevent duplicate serialization of dandiset in detail view [#2125](https://github.com/dandi/dandi-archive/pull/2125) ([@jjnesbitt](https://github.com/jjnesbitt))
- Fix reactivity bug in meditor [#2127](https://github.com/dandi/dandi-archive/pull/2127) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 2

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.4.6 (Wed Jan 08 2025)

#### 🐛 Bug Fix

- Create permissions service layer [#2115](https://github.com/dandi/dandi-archive/pull/2115) ([@jjnesbitt](https://github.com/jjnesbitt))
- Design doc for Upload/AssetBlob garbage collection [#2068](https://github.com/dandi/dandi-archive/pull/2068) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 2

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.4.5 (Fri Jan 03 2025)

#### 🐛 Bug Fix

- Display validation errors on DLP for embargoed dandisets [#2122](https://github.com/dandi/dandi-archive/pull/2122) ([@mvandenburgh](https://github.com/mvandenburgh))

#### 🏠 Internal

- Make logging level of the django app configurable [#2078](https://github.com/dandi/dandi-archive/pull/2078) ([@yarikoptic](https://github.com/yarikoptic) [@waxlamp](https://github.com/waxlamp))

#### Authors: 3

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.4.4 (Thu Jan 02 2025)

#### 🐛 Bug Fix

- Set assets to pending during unembargo [#2117](https://github.com/dandi/dandi-archive/pull/2117) ([@jjnesbitt](https://github.com/jjnesbitt))

#### Authors: 1

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))

---

# v0.4.3 (Fri Dec 27 2024)

#### 🐛 Bug Fix

- Enhance OverviewTab.vue to display Resource Type information for DLP items [#2124](https://github.com/dandi/dandi-archive/pull/2124) ([@bendichter](https://github.com/bendichter))

#### Authors: 1

- Ben Dichter ([@bendichter](https://github.com/bendichter))

---

# v0.4.2 (Thu Dec 19 2024)

#### 🐛 Bug Fix

- Empty commit to trigger release [#2120](https://github.com/dandi/dandi-archive/pull/2120) ([@waxlamp](https://github.com/waxlamp))
- Enable User search by GitHub username [#2119](https://github.com/dandi/dandi-archive/pull/2119) ([@waxlamp](https://github.com/waxlamp))
- DLP: Add "Protocols" card [#2103](https://github.com/dandi/dandi-archive/pull/2103) ([@yarikoptic](https://github.com/yarikoptic) [@waxlamp](https://github.com/waxlamp) [@mvandenburgh](https://github.com/mvandenburgh))
- Login to docker hub only if credentials were provided [#2118](https://github.com/dandi/dandi-archive/pull/2118) ([@yarikoptic](https://github.com/yarikoptic))
- Capitalize `Archive` when it follows `DANDI` [#2114](https://github.com/dandi/dandi-archive/pull/2114) ([@kabilar](https://github.com/kabilar))
- Format template [#2112](https://github.com/dandi/dandi-archive/pull/2112) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 4

- Kabilar Gunalan ([@kabilar](https://github.com/kabilar))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.4.1 (Tue Dec 17 2024)

#### 🐛 Bug Fix

- Set version status to PENDING in ingest_zarr_archive [#2111](https://github.com/dandi/dandi-archive/pull/2111) ([@jjnesbitt](https://github.com/jjnesbitt))

#### Authors: 1

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))

---

# v0.4.0 (Mon Dec 16 2024)

#### 🚀 Enhancement

- Add some .debug level messages in tasks upon no action to be performed [#2079](https://github.com/dandi/dandi-archive/pull/2079) ([@yarikoptic](https://github.com/yarikoptic))

#### 🐛 Bug Fix

- Update shareable link to reflect window.location.origin [#2108](https://github.com/dandi/dandi-archive/pull/2108) (aaronkanzer@Aarons-MacBook-Pro.local [@aaronkanzer](https://github.com/aaronkanzer))
- Update instructions for serving the web app through a development server [#2095](https://github.com/dandi/dandi-archive/pull/2095) ([@candleindark](https://github.com/candleindark))
- Use pre-commit hooks in tox configuration [#2057](https://github.com/dandi/dandi-archive/pull/2057) ([@waxlamp](https://github.com/waxlamp))
- doc: update instruction to natively(locally) run Celery service [#2106](https://github.com/dandi/dandi-archive/pull/2106) ([@candleindark](https://github.com/candleindark) [@mvandenburgh](https://github.com/mvandenburgh))
- DLP: Have "Cite as" only for OPEN (non embargoed) dandisets [#2102](https://github.com/dandi/dandi-archive/pull/2102) ([@yarikoptic](https://github.com/yarikoptic))

#### 🧪 Tests

- ENH: run pytest  against dandi-cli with -v to see which tests ran [#2076](https://github.com/dandi/dandi-archive/pull/2076) ([@yarikoptic](https://github.com/yarikoptic))

#### Authors: 6

- [@aaronkanzer](https://github.com/aaronkanzer)
- Aaron Kanzer (aaronkanzer@Aarons-MacBook-Pro.local)
- Isaac To ([@candleindark](https://github.com/candleindark))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.3.115 (Mon Dec 09 2024)

#### 🐛 Bug Fix

- Bump `django-allauth` to latest version [#2099](https://github.com/dandi/dandi-archive/pull/2099) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.114 (Mon Dec 09 2024)

#### 🐛 Bug Fix

- Pin `django-allauth` to 0.61.1 [#2098](https://github.com/dandi/dandi-archive/pull/2098) ([@mvandenburgh](https://github.com/mvandenburgh))
- Set `--max-warnings` to zero for `eslint` [#2088](https://github.com/dandi/dandi-archive/pull/2088) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.113 (Wed Dec 04 2024)

#### 🐛 Bug Fix

- Fix validation error when only Zarr assets are uploaded [#2062](https://github.com/dandi/dandi-archive/pull/2062) ([@jjnesbitt](https://github.com/jjnesbitt) [@aaronkanzer](https://github.com/aaronkanzer))

#### Authors: 2

- [@aaronkanzer](https://github.com/aaronkanzer)
- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))

---

# v0.3.112 (Mon Dec 02 2024)

#### 🐛 Bug Fix

- Add incomplete upload dialog to DLP when unembargo is blocked [#2082](https://github.com/dandi/dandi-archive/pull/2082) ([@jjnesbitt](https://github.com/jjnesbitt))

#### Authors: 1

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))

---

# v0.3.111 (Mon Dec 02 2024)

:tada: This release contains work from a new contributor! :tada:

Thank you, null[@aaronkanzer](https://github.com/aaronkanzer), for all your work!

#### 🐛 Bug Fix

- Empty PR to trigger release [#2086](https://github.com/dandi/dandi-archive/pull/2086) ([@jjnesbitt](https://github.com/jjnesbitt))
- Include robots.txt in UI and API for handling of web crawlers [#2084](https://github.com/dandi/dandi-archive/pull/2084) (aaronkanzer@Aarons-MacBook-Pro.local [@jjnesbitt](https://github.com/jjnesbitt) [@aaronkanzer](https://github.com/aaronkanzer))
- Use a dedicated logger. not top level logging. module [#2077](https://github.com/dandi/dandi-archive/pull/2077) ([@yarikoptic](https://github.com/yarikoptic))
- Add API support for Embargoed Zarrs [#2069](https://github.com/dandi/dandi-archive/pull/2069) ([@jjnesbitt](https://github.com/jjnesbitt))

#### Authors: 4

- [@aaronkanzer](https://github.com/aaronkanzer)
- Aaron Kanzer (aaronkanzer@Aarons-MacBook-Pro.local)
- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.3.110 (Wed Nov 13 2024)

#### 🐛 Bug Fix

- Fix display of embargoed dandiset error page in GUI [#2073](https://github.com/dandi/dandi-archive/pull/2073) ([@jjnesbitt](https://github.com/jjnesbitt))

#### Authors: 1

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))

---

# v0.3.109 (Thu Oct 31 2024)

#### 🐛 Bug Fix

- Add neurosift external service for dandisets [#2041](https://github.com/dandi/dandi-archive/pull/2041) ([@magland](https://github.com/magland) [@waxlamp](https://github.com/waxlamp))
- Display message in GUI when accessing embargoed dandiset [#2060](https://github.com/dandi/dandi-archive/pull/2060) ([@jjnesbitt](https://github.com/jjnesbitt))

#### Authors: 3

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Jeremy Magland ([@magland](https://github.com/magland))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))

---

# v0.3.108 (Thu Oct 24 2024)

#### 🐛 Bug Fix

- Empty PR to trigger release [#2059](https://github.com/dandi/dandi-archive/pull/2059) ([@mvandenburgh](https://github.com/mvandenburgh))
- Remove `Asset.previous` field [#2008](https://github.com/dandi/dandi-archive/pull/2008) ([@mvandenburgh](https://github.com/mvandenburgh))
- Add pre-commit config and apply it across codebase [#2045](https://github.com/dandi/dandi-archive/pull/2045) ([@yarikoptic](https://github.com/yarikoptic))

#### Authors: 2

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.3.107 (Tue Oct 22 2024)

#### 🐛 Bug Fix

- Update new user registration questions [#2054](https://github.com/dandi/dandi-archive/pull/2054) ([@kabilar](https://github.com/kabilar) [@waxlamp](https://github.com/waxlamp))
- Pin ruff version to avoid spurious test failures [#2053](https://github.com/dandi/dandi-archive/pull/2053) ([@waxlamp](https://github.com/waxlamp))
- Pin ubuntu-22.04 for all CI jobs [#2056](https://github.com/dandi/dandi-archive/pull/2056) ([@waxlamp](https://github.com/waxlamp))

#### Authors: 2

- Kabilar Gunalan ([@kabilar](https://github.com/kabilar))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))

---

# v0.3.106 (Thu Oct 17 2024)

#### 🐛 Bug Fix

- Derive asset `access` field from asset blob [#2010](https://github.com/dandi/dandi-archive/pull/2010) ([@jjnesbitt](https://github.com/jjnesbitt))
- Add command for asset metadata re-extraction [#1545](https://github.com/dandi/dandi-archive/pull/1545) ([@jjnesbitt](https://github.com/jjnesbitt))
- Explicitly install Python in CD workflows [#2046](https://github.com/dandi/dandi-archive/pull/2046) ([@mvandenburgh](https://github.com/mvandenburgh))
- Auto-allow people with @alleninstitute.org email addresses [#2044](https://github.com/dandi/dandi-archive/pull/2044) ([@yarikoptic](https://github.com/yarikoptic))

#### 🏠 Internal

- Add calculate_sha256 management command to trigger (re)computation for a blob [#1938](https://github.com/dandi/dandi-archive/pull/1938) ([@yarikoptic](https://github.com/yarikoptic) [@waxlamp](https://github.com/waxlamp))

#### 🧪 Tests

- Do login into docker hub so we could reliably build our docker image [#2043](https://github.com/dandi/dandi-archive/pull/2043) ([@yarikoptic](https://github.com/yarikoptic))
- Stick to ubuntu-22.04 for now for frontend-ci.yml [#2042](https://github.com/dandi/dandi-archive/pull/2042) ([@yarikoptic](https://github.com/yarikoptic))

#### Authors: 4

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.3.105 (Mon Sep 23 2024)

#### 🐛 Bug Fix

- Fix Dandiset emptiness detection logic [#2035](https://github.com/dandi/dandi-archive/pull/2035) ([@waxlamp](https://github.com/waxlamp))

#### Authors: 1

- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))

---

# v0.3.104 (Mon Sep 23 2024)

#### 🐛 Bug Fix

- ../assets/{asset_id}/ PUT: clarify that new asset is created [#2019](https://github.com/dandi/dandi-archive/pull/2019) ([@yarikoptic](https://github.com/yarikoptic))

#### Authors: 1

- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.3.103 (Mon Sep 23 2024)

#### 🐛 Bug Fix

- add external neurosift service for .nwb.lindi.tar [#2030](https://github.com/dandi/dandi-archive/pull/2030) ([@magland](https://github.com/magland))

#### Authors: 1

- Jeremy Magland ([@magland](https://github.com/magland))

---

# v0.3.102 (Fri Sep 20 2024)

:tada: This release contains work from a new contributor! :tada:

Thank you, null[@aaronkanzer](https://github.com/aaronkanzer), for all your work!

#### 🐛 Bug Fix

- Empty PR to force a release [#2032](https://github.com/dandi/dandi-archive/pull/2032) ([@waxlamp](https://github.com/waxlamp))
- For staging environment, include dynamic text for `dandi download` command [#1810](https://github.com/dandi/dandi-archive/pull/1810) (aaronkanzer@Aarons-MacBook-Pro.local [@waxlamp](https://github.com/waxlamp) [@aaronkanzer](https://github.com/aaronkanzer))

#### Authors: 4

- [@aaronkanzer](https://github.com/aaronkanzer)
- Aaron Kanzer (aaronkanzer@Aarons-MacBook-Pro.local)
- Aaron Kanzer (aaronkanzer@dhcp-10-29-239-233.dyn.MIT.EDU)
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))

---

# v0.3.101 (Fri Sep 20 2024)

:tada: This release contains work from a new contributor! :tada:

Thank you, null[@aaronkanzer](https://github.com/aaronkanzer), for all your work!

#### 🐛 Bug Fix

- Only include APPROVED users for stats on homepage [#1952](https://github.com/dandi/dandi-archive/pull/1952) (aaronkanzer@Aarons-MacBook-Pro.local [@aaronkanzer](https://github.com/aaronkanzer) [@waxlamp](https://github.com/waxlamp))

#### Authors: 3

- [@aaronkanzer](https://github.com/aaronkanzer)
- Aaron Kanzer (aaronkanzer@Aarons-MacBook-Pro.local)
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))

---

# v0.3.100 (Fri Sep 20 2024)

#### 🐛 Bug Fix

- Add text from the Handbook to the rejected user email [#2022](https://github.com/dandi/dandi-archive/pull/2022) ([@kabilar](https://github.com/kabilar))

#### Authors: 1

- Kabilar Gunalan ([@kabilar](https://github.com/kabilar))

---

# v0.3.99 (Tue Sep 10 2024)

#### 🐛 Bug Fix

- Manually configure celery to retry connections on startup [#2026](https://github.com/dandi/dandi-archive/pull/2026) ([@danlamanna](https://github.com/danlamanna))

#### Authors: 1

- Dan LaManna ([@danlamanna](https://github.com/danlamanna))

---

# v0.3.98 (Tue Sep 10 2024)

#### 🐛 Bug Fix

- admin view: Also show (list) zarr for Assets view [#2017](https://github.com/dandi/dandi-archive/pull/2017) ([@yarikoptic](https://github.com/yarikoptic))

#### Authors: 1

- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.3.97 (Tue Sep 10 2024)

#### 🐛 Bug Fix

- Disable GUI "Unembargo" button if there are active uploads [#2015](https://github.com/dandi/dandi-archive/pull/2015) ([@jjnesbitt](https://github.com/jjnesbitt))

#### Authors: 1

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))

---

# v0.3.96 (Mon Sep 09 2024)

#### 🐛 Bug Fix

- Use bulk_update for updating blob download counts [#2025](https://github.com/dandi/dandi-archive/pull/2025) ([@danlamanna](https://github.com/danlamanna))

#### Authors: 1

- Dan LaManna ([@danlamanna](https://github.com/danlamanna))

---

# v0.3.95 (Tue Aug 27 2024)

#### 🐛 Bug Fix

- Respond with 409 when creating duplicate asset blobs [#2011](https://github.com/dandi/dandi-archive/pull/2011) ([@danlamanna](https://github.com/danlamanna))
- Apply new `ruff` rules [#2009](https://github.com/dandi/dandi-archive/pull/2009) ([@mvandenburgh](https://github.com/mvandenburgh))
- Add Neurosift service for AVI files [#1983](https://github.com/dandi/dandi-archive/pull/1983) ([@magland](https://github.com/magland))

#### 🏠 Internal

- [gh-actions](deps): Bump actions/add-to-project from 0.6.0 to 1.0.2 [#1962](https://github.com/dandi/dandi-archive/pull/1962) ([@dependabot[bot]](https://github.com/dependabot[bot]))

#### Authors: 4

- [@dependabot[bot]](https://github.com/dependabot[bot])
- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Jeremy Magland ([@magland](https://github.com/magland))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.94 (Fri Aug 16 2024)

#### 🐛 Bug Fix

- Fix admin access to embargoed asset blobs [#2004](https://github.com/dandi/dandi-archive/pull/2004) ([@jjnesbitt](https://github.com/jjnesbitt))
- Re-validate version metadata during unembargo [#1989](https://github.com/dandi/dandi-archive/pull/1989) ([@jjnesbitt](https://github.com/jjnesbitt))
- Separate core model logic from top-level asset service layer functions [#1991](https://github.com/dandi/dandi-archive/pull/1991) ([@jjnesbitt](https://github.com/jjnesbitt))

#### Authors: 1

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))

---

# v0.3.93 (Wed Aug 14 2024)

#### 🐛 Bug Fix

- Empty commit to trigger release process [#2005](https://github.com/dandi/dandi-archive/pull/2005) ([@waxlamp](https://github.com/waxlamp))
- Upgrade oauth client package [#1998](https://github.com/dandi/dandi-archive/pull/1998) ([@mvandenburgh](https://github.com/mvandenburgh))
- Merge remote-tracking branch 'origin/master' into audit-backend [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Replace `docker-compose` with `docker compose` to fix newly failing CI tests [#1999](https://github.com/dandi/dandi-archive/pull/1999) ([@waxlamp](https://github.com/waxlamp))
- Merge remote-tracking branch 'origin/fix-docker-compose' into audit-backend [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Add test for publish_dandiset audit record [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Disable complexity warning on users view [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Add explanatory comment [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Use nested transaction to handle integrity error [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Split long tests up into individual tests [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- bugfix: Pass correct and stringified ID values in asset/zarr records [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- bugfix: Include correct asset in update_asset record [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Add tests [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Fix invocation of unembargo routines in tests [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Remove duplicate task launch line [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Remove references to deleted model fields [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Use audit service in zarr views [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Eliminate the need for manually calling .save() [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Create a service layer module for audit [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Use the `user` fixture directly [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Reformat long line [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Suppress ruff warnings for complexity and number of arguments [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Report list of paths to zarr chunk audit records [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Report live metadata to audit records [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Move "set new owners" operation inside of transaction [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Remove Dandiset add_owner() and remove_owner() methods [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Apply formatting to new migration [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Add explanatory comments for weird char field length limits [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Rename upload_zarr to upload_zarr_chunks [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Fix tests broken by signature changes [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Add migration for AuditRecord [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Generate delete_dandiset audit record [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Generate publish_dandiset audit record [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Generate unembargo_dandiset audit record [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Generate [create|upload|finalize|delete]_zarr audit records [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Generate [add|update|remove]_asset audit records [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Generate update_metadata audit record [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Generate change_owners audit record [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Generate create_dandiset audit record [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Add admin model for AuditRecord [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))
- Add AuditRecord model [#1886](https://github.com/dandi/dandi-archive/pull/1886) ([@waxlamp](https://github.com/waxlamp))

#### Authors: 2

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))

---

# v0.3.92 (Tue Jul 30 2024)

#### 🐛 Bug Fix

- Add retries to sha256 checksum calculation task [#1937](https://github.com/dandi/dandi-archive/pull/1937) ([@jjnesbitt](https://github.com/jjnesbitt))
- Contact owner [#1840](https://github.com/dandi/dandi-archive/pull/1840) ([@marySalvi](https://github.com/marySalvi) [@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 3

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Mary Salvi ([@marySalvi](https://github.com/marySalvi))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.91 (Wed Jul 24 2024)

#### 🐛 Bug Fix

- Fix N query problem with VersionStatusFilter [#1986](https://github.com/dandi/dandi-archive/pull/1986) ([@jjnesbitt](https://github.com/jjnesbitt))

#### Authors: 1

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))

---

# v0.3.90 (Mon Jul 22 2024)

#### 🐛 Bug Fix

- Automate dandiset unembargo [#1965](https://github.com/dandi/dandi-archive/pull/1965) ([@jjnesbitt](https://github.com/jjnesbitt))

#### Authors: 1

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))

---

# v0.3.89 (Fri Jul 19 2024)

#### 🐛 Bug Fix

- Add dashboard link to view to emit user list as Mailchimp-compatible CSV [#1979](https://github.com/dandi/dandi-archive/pull/1979) ([@waxlamp](https://github.com/waxlamp))

#### Authors: 1

- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))

---

# v0.3.88 (Mon Jul 15 2024)

#### 🐛 Bug Fix

- Bump dandischema to 0.10.2 (schema version 0.6.8) [#1976](https://github.com/dandi/dandi-archive/pull/1976) ([@jjnesbitt](https://github.com/jjnesbitt))
- Pin updated dependencies [#1977](https://github.com/dandi/dandi-archive/pull/1977) ([@jjnesbitt](https://github.com/jjnesbitt))
- Suppress lint error (SIM103) [#1973](https://github.com/dandi/dandi-archive/pull/1973) ([@jjnesbitt](https://github.com/jjnesbitt))
- Remove File to avoid confusion [#1972](https://github.com/dandi/dandi-archive/pull/1972) ([@yarikoptic](https://github.com/yarikoptic))

#### Authors: 2

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.3.87 (Fri Jun 21 2024)

#### 🐛 Bug Fix

- Lock dandisets during un-embargo [#1957](https://github.com/dandi/dandi-archive/pull/1957) ([@jjnesbitt](https://github.com/jjnesbitt))

#### Authors: 1

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))

---

# v0.3.86 (Tue Jun 18 2024)

#### 🐛 Bug Fix

- Restrict updates to metadata `access` field [#1954](https://github.com/dandi/dandi-archive/pull/1954) ([@jjnesbitt](https://github.com/jjnesbitt))
- Fix race condition in sha256 calculation task [#1936](https://github.com/dandi/dandi-archive/pull/1936) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 2

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.85 (Mon Jun 03 2024)

:tada: This release contains work from a new contributor! :tada:

Thank you, Ben Dichter ([@bendichter](https://github.com/bendichter)), for all your work!

#### 🐛 Bug Fix

- Empty PR to trigger a release [#1951](https://github.com/dandi/dandi-archive/pull/1951) ([@jjnesbitt](https://github.com/jjnesbitt))
- Only use custom pagination class for asset list endpoint [#1947](https://github.com/dandi/dandi-archive/pull/1947) ([@jjnesbitt](https://github.com/jjnesbitt))
- In 1.14.3 it became client_config and .config was announced deprecated [#1946](https://github.com/dandi/dandi-archive/pull/1946) ([@yarikoptic](https://github.com/yarikoptic))
- neurosift external service for .nwb.lindi.json [#1922](https://github.com/dandi/dandi-archive/pull/1922) ([@magland](https://github.com/magland))
- Fix documentation for server downtime message var [#1927](https://github.com/dandi/dandi-archive/pull/1927) ([@jjnesbitt](https://github.com/jjnesbitt))
- Revert "Add `workflow_dispatch` trigger to staging deploy workflow" [#1930](https://github.com/dandi/dandi-archive/pull/1930) ([@jjnesbitt](https://github.com/jjnesbitt))

#### 📝 Documentation

- add handbook to welcome email [#1945](https://github.com/dandi/dandi-archive/pull/1945) ([@bendichter](https://github.com/bendichter))

#### Authors: 4

- Ben Dichter ([@bendichter](https://github.com/bendichter))
- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Jeremy Magland ([@magland](https://github.com/magland))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.3.84 (Mon Apr 29 2024)

#### 🐛 Bug Fix

- Remove all-contributors auto plugin [#1928](https://github.com/dandi/dandi-archive/pull/1928) ([@jjnesbitt](https://github.com/jjnesbitt))
- Embargo Re-Design [#1890](https://github.com/dandi/dandi-archive/pull/1890) ([@jjnesbitt](https://github.com/jjnesbitt) [@mvandenburgh](https://github.com/mvandenburgh))
- Remove unnecessary `noqa` directive [#1926](https://github.com/dandi/dandi-archive/pull/1926) ([@jjnesbitt](https://github.com/jjnesbitt))
- Update our instructions for installation to state newer versions of python and dandi-cli [#1919](https://github.com/dandi/dandi-archive/pull/1919) ([@yarikoptic](https://github.com/yarikoptic))
- Add `workflow_dispatch` trigger to staging deploy workflow [#1924](https://github.com/dandi/dandi-archive/pull/1924) ([@mvandenburgh](https://github.com/mvandenburgh))
- Optimize asset permission check function [#1912](https://github.com/dandi/dandi-archive/pull/1912) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 3

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.3.83 (Mon Apr 01 2024)

#### 🐛 Bug Fix

- Add default ordering to paginated models [#1910](https://github.com/dandi/dandi-archive/pull/1910) ([@jjnesbitt](https://github.com/jjnesbitt))

#### Authors: 1

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))

---

# v0.3.82 (Fri Mar 29 2024)

#### 🐛 Bug Fix

- Only include total count in the first page of list views [#1911](https://github.com/dandi/dandi-archive/pull/1911) ([@jjnesbitt](https://github.com/jjnesbitt))

#### Authors: 1

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))

---

# v0.3.81 (Mon Mar 25 2024)

#### 🐛 Bug Fix

- Optimize asset list endpoint [#1904](https://github.com/dandi/dandi-archive/pull/1904) ([@jjnesbitt](https://github.com/jjnesbitt))
- Revert rate limiting of asset list endpoint [#1905](https://github.com/dandi/dandi-archive/pull/1905) ([@mvandenburgh](https://github.com/mvandenburgh))
- Add missing setting for DRF throttle class [#1903](https://github.com/dandi/dandi-archive/pull/1903) ([@mvandenburgh](https://github.com/mvandenburgh))
- Rate limit assets list endpoint for unauthenticated users [#1899](https://github.com/dandi/dandi-archive/pull/1899) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 2

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.80 (Thu Mar 21 2024)

#### 🐛 Bug Fix

- Temporarily pin DRF [#1895](https://github.com/dandi/dandi-archive/pull/1895) ([@mvandenburgh](https://github.com/mvandenburgh))
- Improve Swagger documentation for /dandisets/ query params [#1875](https://github.com/dandi/dandi-archive/pull/1875) ([@mvandenburgh](https://github.com/mvandenburgh))

#### 🏠 Internal

- Boost dandischema to 0.10.1 which released 0.6.7 schema [#1893](https://github.com/dandi/dandi-archive/pull/1893) ([@yarikoptic](https://github.com/yarikoptic))

#### Authors: 2

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.3.79 (Thu Mar 07 2024)

#### 🐛 Bug Fix

- Change asset path collation to "C" [#1888](https://github.com/dandi/dandi-archive/pull/1888) ([@jjnesbitt](https://github.com/jjnesbitt))

#### Authors: 1

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))

---

# v0.3.78 (Wed Mar 06 2024)

#### 🐛 Bug Fix

- Use different collation for Asset `path` field [#1885](https://github.com/dandi/dandi-archive/pull/1885) ([@jjnesbitt](https://github.com/jjnesbitt))
- Run all linting commands, even if some of them fail [#1882](https://github.com/dandi/dandi-archive/pull/1882) ([@waxlamp](https://github.com/waxlamp))
- Add format changes from ruff update [#1883](https://github.com/dandi/dandi-archive/pull/1883) ([@marySalvi](https://github.com/marySalvi))
- Update Heroku Python runtime [#1876](https://github.com/dandi/dandi-archive/pull/1876) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 4

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Mary Salvi ([@marySalvi](https://github.com/marySalvi))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))

---

# v0.3.77 (Thu Feb 29 2024)

:tada: This release contains work from new contributors! :tada:

Thanks for all your work!

:heart: Isaac To ([@candleindark](https://github.com/candleindark))

:heart: Kabilar Gunalan ([@kabilar](https://github.com/kabilar))

#### 🐛 Bug Fix

- Require v0.60.0 of `dandi-cli` [#1878](https://github.com/dandi/dandi-archive/pull/1878) ([@mvandenburgh](https://github.com/mvandenburgh))
- Update VJSF to 2.23.3 [#1874](https://github.com/dandi/dandi-archive/pull/1874) ([@mvandenburgh](https://github.com/mvandenburgh))
- Design doc for Audit MVP [#1801](https://github.com/dandi/dandi-archive/pull/1801) ([@waxlamp](https://github.com/waxlamp))
- Fix `UserMetadata` not being created if `createsuperuser` script is used [#1113](https://github.com/dandi/dandi-archive/pull/1113) ([@mvandenburgh](https://github.com/mvandenburgh))
- Boost dandischema to 0.9.* series so we get support for pydantic 2.0 and schema 0.6.5 [#1823](https://github.com/dandi/dandi-archive/pull/1823) ([@yarikoptic](https://github.com/yarikoptic) [@candleindark](https://github.com/candleindark) [@mvandenburgh](https://github.com/mvandenburgh))
- Add e2e test for meditor validation [#1865](https://github.com/dandi/dandi-archive/pull/1865) ([@mvandenburgh](https://github.com/mvandenburgh))
- Add .DS_Store to .gitignore [#1863](https://github.com/dandi/dandi-archive/pull/1863) ([@kabilar](https://github.com/kabilar))

#### 🏠 Internal

- [gh-actions](deps): Bump actions/add-to-project from 0.5.0 to 0.6.0 [#1872](https://github.com/dandi/dandi-archive/pull/1872) ([@dependabot[bot]](https://github.com/dependabot[bot]))

#### Authors: 6

- [@dependabot[bot]](https://github.com/dependabot[bot])
- Isaac To ([@candleindark](https://github.com/candleindark))
- Kabilar Gunalan ([@kabilar](https://github.com/kabilar))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.3.76 (Wed Feb 14 2024)

#### 🐛 Bug Fix

- Don't use .save() in validate_version_metadata [#1800](https://github.com/dandi/dandi-archive/pull/1800) ([@jjnesbitt](https://github.com/jjnesbitt))
- Add quirks section to embargo redesign doc [#1802](https://github.com/dandi/dandi-archive/pull/1802) ([@waxlamp](https://github.com/waxlamp))
- Remove obsolete/not-applicable TODO [#1829](https://github.com/dandi/dandi-archive/pull/1829) ([@yarikoptic](https://github.com/yarikoptic))
- Don't use filesystem APIs to manipulate URLs [#1782](https://github.com/dandi/dandi-archive/pull/1782) ([@brianhelba](https://github.com/brianhelba))

#### 📝 Documentation

- DEVELOPMENT.md: set email to the one known to git [#1828](https://github.com/dandi/dandi-archive/pull/1828) ([@yarikoptic](https://github.com/yarikoptic) [@waxlamp](https://github.com/waxlamp))

#### Authors: 4

- Brian Helba ([@brianhelba](https://github.com/brianhelba))
- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.3.75 (Fri Feb 09 2024)

#### 🐛 Bug Fix

- Open asset on click [#1847](https://github.com/dandi/dandi-archive/pull/1847) ([@waxlamp](https://github.com/waxlamp))
- Improve file browser view action icons [#1846](https://github.com/dandi/dandi-archive/pull/1846) ([@waxlamp](https://github.com/waxlamp))
- Add a Nix Flake for native build dependencies [#1843](https://github.com/dandi/dandi-archive/pull/1843) ([@waxlamp](https://github.com/waxlamp))
- Add tooltips to describe FileBrowserView action icons [#1845](https://github.com/dandi/dandi-archive/pull/1845) ([@waxlamp](https://github.com/waxlamp))
- Build project with `build` & `pyproject.toml` [#1855](https://github.com/dandi/dandi-archive/pull/1855) ([@jwodder](https://github.com/jwodder))
- Fix lint errors [#1854](https://github.com/dandi/dandi-archive/pull/1854) ([@waxlamp](https://github.com/waxlamp))

#### 📝 Documentation

- Fix documentation about release process to Heroku -- done by GitHub CI now not Heroku itself [#1856](https://github.com/dandi/dandi-archive/pull/1856) ([@yarikoptic](https://github.com/yarikoptic) [@waxlamp](https://github.com/waxlamp))

#### Authors: 3

- John T. Wodder II ([@jwodder](https://github.com/jwodder))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.3.74 (Wed Feb 07 2024)

#### 🐛 Bug Fix

- Fix remaining problems with version display [#1860](https://github.com/dandi/dandi-archive/pull/1860) ([@waxlamp](https://github.com/waxlamp))

#### Authors: 1

- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))

---

# v0.3.73 (Tue Feb 06 2024)

#### 🐛 Bug Fix

- Always rebuild and deploy the frontend [#1857](https://github.com/dandi/dandi-archive/pull/1857) ([@waxlamp](https://github.com/waxlamp))
- Use Ruff for Python static analysis and formatting [#1784](https://github.com/dandi/dandi-archive/pull/1784) ([@brianhelba](https://github.com/brianhelba) [@mvandenburgh](https://github.com/mvandenburgh))

#### 🏠 Internal

- It is time again to get to the new year and update Copyright statement [#1852](https://github.com/dandi/dandi-archive/pull/1852) ([@yarikoptic](https://github.com/yarikoptic))
- [gh-actions](deps): Bump actions/cache from 3 to 4 [#1822](https://github.com/dandi/dandi-archive/pull/1822) ([@dependabot[bot]](https://github.com/dependabot[bot]))

#### Authors: 5

- [@dependabot[bot]](https://github.com/dependabot[bot])
- Brian Helba ([@brianhelba](https://github.com/brianhelba))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.3.72 (Tue Jan 16 2024)

#### 🐛 Bug Fix

- Retry aggregate_assets_summary_task on version metadata race condition [#1803](https://github.com/dandi/dandi-archive/pull/1803) ([@jjnesbitt](https://github.com/jjnesbitt))
- Add an e2e test for the FileBrowser [#1789](https://github.com/dandi/dandi-archive/pull/1789) ([@marySalvi](https://github.com/marySalvi))

#### Authors: 2

- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Mary Salvi ([@marySalvi](https://github.com/marySalvi))

---

# v0.3.71 (Thu Jan 04 2024)

#### 🐛 Bug Fix

- Check if version still exists before proceeding with validation [#1808](https://github.com/dandi/dandi-archive/pull/1808) ([@mvandenburgh](https://github.com/mvandenburgh))
- Generate correct docs for dandisets endpoint [#1807](https://github.com/dandi/dandi-archive/pull/1807) ([@waxlamp](https://github.com/waxlamp))

#### Authors: 2

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))

---

# v0.3.70 (Wed Jan 03 2024)

#### 🐛 Bug Fix

- Return 401 on unauthenticated embargo dandiset list [#1790](https://github.com/dandi/dandi-archive/pull/1790) ([@jjnesbitt](https://github.com/jjnesbitt))
- Remove `requirements.txt` file [#1798](https://github.com/dandi/dandi-archive/pull/1798) ([@mvandenburgh](https://github.com/mvandenburgh))

#### 🏠 Internal

- [gh-actions](deps): Bump actions/download-artifact from 3 to 4 [#1793](https://github.com/dandi/dandi-archive/pull/1793) ([@dependabot[bot]](https://github.com/dependabot[bot]) [@mvandenburgh](https://github.com/mvandenburgh))
- [gh-actions](deps): Bump actions/upload-artifact from 3 to 4 [#1794](https://github.com/dandi/dandi-archive/pull/1794) ([@dependabot[bot]](https://github.com/dependabot[bot]))

#### Authors: 3

- [@dependabot[bot]](https://github.com/dependabot[bot])
- Jacob Nesbitt ([@jjnesbitt](https://github.com/jjnesbitt))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.69 (Wed Dec 20 2023)

#### 🐛 Bug Fix

- Approval view: automatically redirect back to page after authentication [#1786](https://github.com/dandi/dandi-archive/pull/1786) ([@mvandenburgh](https://github.com/mvandenburgh))
- Remove explicit dependency on `pydantic` [#1796](https://github.com/dandi/dandi-archive/pull/1796) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.68 (Wed Dec 20 2023)

#### 🐛 Bug Fix

- Update + Reconfigure Vue Sentry SDK [#1795](https://github.com/dandi/dandi-archive/pull/1795) ([@mvandenburgh](https://github.com/mvandenburgh))
- Remove old squashed migrations [#1778](https://github.com/dandi/dandi-archive/pull/1778) ([@brianhelba](https://github.com/brianhelba))
- Fix S101 Use of `assert` detected [#1783](https://github.com/dandi/dandi-archive/pull/1783) ([@brianhelba](https://github.com/brianhelba))

#### Authors: 2

- Brian Helba ([@brianhelba](https://github.com/brianhelba))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.67 (Thu Dec 14 2023)

#### 🐛 Bug Fix

- Convert `rest.ts` to composition API [#1774](https://github.com/dandi/dandi-archive/pull/1774) ([@mvandenburgh](https://github.com/mvandenburgh))
- Add login redirect to user dashboard [#1781](https://github.com/dandi/dandi-archive/pull/1781) ([@mvandenburgh](https://github.com/mvandenburgh))
- Add embargo re-design doc [#1772](https://github.com/dandi/dandi-archive/pull/1772) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Ensure that creating the default OAuth2 Application works on staging [#1779](https://github.com/dandi/dandi-archive/pull/1779) ([@brianhelba](https://github.com/brianhelba))
- Squash migrations for "api", "analytics", and "zarr" apps [#1777](https://github.com/dandi/dandi-archive/pull/1777) ([@brianhelba](https://github.com/brianhelba))
- Fix issues found by Ruff [#1776](https://github.com/dandi/dandi-archive/pull/1776) ([@brianhelba](https://github.com/brianhelba))
- Switch frontend build process from Webpack to Vite [#1725](https://github.com/dandi/dandi-archive/pull/1725) ([@mvandenburgh](https://github.com/mvandenburgh))
- Fix FBT001 Boolean-typed positional argument in function definition [#1765](https://github.com/dandi/dandi-archive/pull/1765) ([@brianhelba](https://github.com/brianhelba))
- Fix RET505 Unnecessary `else` / `elif` after `return` statement [#1752](https://github.com/dandi/dandi-archive/pull/1752) ([@brianhelba](https://github.com/brianhelba))
- Avoid clobbering version metadata when calculating assets summary [#1557](https://github.com/dandi/dandi-archive/pull/1557) ([@danlamanna](https://github.com/danlamanna))
- Add upload/asset blob garbage collection design doc [#1733](https://github.com/dandi/dandi-archive/pull/1733) ([@mvandenburgh](https://github.com/mvandenburgh))
- Fix DJ008 Model does not define `__str__` method [#1767](https://github.com/dandi/dandi-archive/pull/1767) ([@brianhelba](https://github.com/brianhelba))
- [FIX] serviceUrl replacement [#1770](https://github.com/dandi/dandi-archive/pull/1770) ([@magland](https://github.com/magland))

#### 🏠 Internal

- [gh-actions](deps): Bump actions/setup-python from 4 to 5 [#1780](https://github.com/dandi/dandi-archive/pull/1780) ([@dependabot[bot]](https://github.com/dependabot[bot]))
- `test_zarr.py`: Import `EMPTY_CHECKSUM` from `zarr_checksum` [#1775](https://github.com/dandi/dandi-archive/pull/1775) ([@jwodder](https://github.com/jwodder))

#### Authors: 7

- [@dependabot[bot]](https://github.com/dependabot[bot])
- Brian Helba ([@brianhelba](https://github.com/brianhelba))
- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Jeremy Magland ([@magland](https://github.com/magland))
- John T. Wodder II ([@jwodder](https://github.com/jwodder))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.66 (Fri Dec 01 2023)

#### 🐛 Bug Fix

- Fix invalid contributors causing crash [#1771](https://github.com/dandi/dandi-archive/pull/1771) ([@mvandenburgh](https://github.com/mvandenburgh))
- Remove unnecessary quote escaping [#1766](https://github.com/dandi/dandi-archive/pull/1766) ([@brianhelba](https://github.com/brianhelba))
- Fix a test failure [#1768](https://github.com/dandi/dandi-archive/pull/1768) ([@brianhelba](https://github.com/brianhelba))
- Fix issues found by Ruff [#1763](https://github.com/dandi/dandi-archive/pull/1763) ([@brianhelba](https://github.com/brianhelba))
- WIP: Fix RET503 Missing explicit `return` at the end of function able to return non-`None` value [#1762](https://github.com/dandi/dandi-archive/pull/1762) ([@brianhelba](https://github.com/brianhelba))
- Fix issues found by Ruff [#1748](https://github.com/dandi/dandi-archive/pull/1748) ([@brianhelba](https://github.com/brianhelba))
- Fix G004 Logging statement uses f-string [#1750](https://github.com/dandi/dandi-archive/pull/1750) ([@brianhelba](https://github.com/brianhelba))
- Fix S113 Probable use of requests call without timeout [#1751](https://github.com/dandi/dandi-archive/pull/1751) ([@brianhelba](https://github.com/brianhelba))
- Upgrade django-s3-file-field [#1735](https://github.com/dandi/dandi-archive/pull/1735) ([@brianhelba](https://github.com/brianhelba))
- Fix N818 Exception name should be named with an Error suffix [#1749](https://github.com/dandi/dandi-archive/pull/1749) ([@brianhelba](https://github.com/brianhelba))

#### Authors: 2

- Brian Helba ([@brianhelba](https://github.com/brianhelba))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.65 (Wed Nov 22 2023)

#### 🐛 Bug Fix

- Check that path is an asset before proceeding [#1759](https://github.com/dandi/dandi-archive/pull/1759) ([@AlmightyYakob](https://github.com/AlmightyYakob))

#### Authors: 1

- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))

---

# v0.3.64 (Wed Nov 22 2023)

#### 🐛 Bug Fix

- adjust neurosift service endpoint URL, passing additional info [#1706](https://github.com/dandi/dandi-archive/pull/1706) ([@magland](https://github.com/magland) [@waxlamp](https://github.com/waxlamp))
- Optimize dandiset owner PUT endpoint [#1737](https://github.com/dandi/dandi-archive/pull/1737) ([@mvandenburgh](https://github.com/mvandenburgh) [@AlmightyYakob](https://github.com/AlmightyYakob))

#### Authors: 4

- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Jeremy Magland ([@magland](https://github.com/magland))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))

---

# v0.3.63 (Tue Nov 21 2023)

#### 🐛 Bug Fix

- Fix race condition in version PUT endpoint [#1757](https://github.com/dandi/dandi-archive/pull/1757) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.62 (Fri Nov 17 2023)

#### 🐛 Bug Fix

- [DATALAD RUNCMD] Replace youtube URL with the one with @dandiarchive [#1754](https://github.com/dandi/dandi-archive/pull/1754) ([@yarikoptic](https://github.com/yarikoptic))
- Fix style issues found by Ruff [#1741](https://github.com/dandi/dandi-archive/pull/1741) ([@brianhelba](https://github.com/brianhelba))

#### Authors: 2

- Brian Helba ([@brianhelba](https://github.com/brianhelba))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.3.61 (Thu Nov 09 2023)

#### 🐛 Bug Fix

- Fix S308 Use of `mark_safe` may expose cross-site scripting vulnerabilities [#1742](https://github.com/dandi/dandi-archive/pull/1742) ([@brianhelba](https://github.com/brianhelba))
- Clean up and improve the performance of manifest file creation [#1738](https://github.com/dandi/dandi-archive/pull/1738) ([@brianhelba](https://github.com/brianhelba))
- Fix PTH118 `os.path.join()` should be replaced by `Path` with `/` operator [#1743](https://github.com/dandi/dandi-archive/pull/1743) ([@brianhelba](https://github.com/brianhelba))

#### Authors: 1

- Brian Helba ([@brianhelba](https://github.com/brianhelba))

---

# v0.3.60 (Tue Nov 07 2023)

#### 🐛 Bug Fix

- Add UPLOADED state to Zarr models [#1698](https://github.com/dandi/dandi-archive/pull/1698) ([@AlmightyYakob](https://github.com/AlmightyYakob) [@danlamanna](https://github.com/danlamanna))
- Require Python 3.11 [#1736](https://github.com/dandi/dandi-archive/pull/1736) ([@brianhelba](https://github.com/brianhelba))
- Add a note to registration page that no account is necessary to access public data [#1696](https://github.com/dandi/dandi-archive/pull/1696) ([@yarikoptic](https://github.com/yarikoptic) [@satra](https://github.com/satra))

#### 🧪 Tests

- Revert "Skip broken dandi-cli tests" - fixed up in dandi-cli 0.57.0 [#1732](https://github.com/dandi/dandi-archive/pull/1732) ([@yarikoptic](https://github.com/yarikoptic))

#### Authors: 5

- Brian Helba ([@brianhelba](https://github.com/brianhelba))
- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Satrajit Ghosh ([@satra](https://github.com/satra))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.3.59 (Fri Oct 27 2023)

#### 🐛 Bug Fix

- Optimize dandiset listing endpoint [#1730](https://github.com/dandi/dandi-archive/pull/1730) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Update `django-composed-configuration` [#1731](https://github.com/dandi/dandi-archive/pull/1731) ([@mvandenburgh](https://github.com/mvandenburgh))

#### 🏠 Internal

- [gh-actions](deps): Bump actions/setup-node from 3 to 4 [#1726](https://github.com/dandi/dandi-archive/pull/1726) ([@dependabot[bot]](https://github.com/dependabot[bot]))

#### Authors: 3

- [@dependabot[bot]](https://github.com/dependabot[bot])
- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.58 (Wed Oct 25 2023)

#### 🐛 Bug Fix

- Add sentry profiling [#1728](https://github.com/dandi/dandi-archive/pull/1728) ([@danlamanna](https://github.com/danlamanna))
- Remove unnecessary atomic decorators from tasks [#1720](https://github.com/dandi/dandi-archive/pull/1720) ([@mvandenburgh](https://github.com/mvandenburgh))
- Remove pinning on django-storages[boto3] [#1717](https://github.com/dandi/dandi-archive/pull/1717) ([@mvandenburgh](https://github.com/mvandenburgh))
- Temporarily skip broken dandi-cli tests [#1718](https://github.com/dandi/dandi-archive/pull/1718) ([@mvandenburgh](https://github.com/mvandenburgh))
- Remove unused `modified` field on `Upload` model [#1713](https://github.com/dandi/dandi-archive/pull/1713) ([@mvandenburgh](https://github.com/mvandenburgh))
- File page index fix [#1704](https://github.com/dandi/dandi-archive/pull/1704) ([@marySalvi](https://github.com/marySalvi))
- Fix `requests` type errors [#1714](https://github.com/dandi/dandi-archive/pull/1714) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 3

- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Mary Salvi ([@marySalvi](https://github.com/marySalvi))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.57 (Mon Oct 16 2023)

#### 🐛 Bug Fix

- Upgrade `dandischema` dependency [#1703](https://github.com/dandi/dandi-archive/pull/1703) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.56 (Thu Oct 12 2023)

#### 🐛 Bug Fix

- Align Postgres tables/indexes/constraints with Django [#1697](https://github.com/dandi/dandi-archive/pull/1697) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Prevent CHANGELOG.md from triggering staging deploy [#1699](https://github.com/dandi/dandi-archive/pull/1699) ([@waxlamp](https://github.com/waxlamp))

#### Authors: 2

- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))

---

# v0.3.55 (Wed Oct 04 2023)

#### 🐛 Bug Fix

- Enable path-only changes to metadata to trigger asset change [#1689](https://github.com/dandi/dandi-archive/pull/1689) ([@waxlamp](https://github.com/waxlamp) [@AlmightyYakob](https://github.com/AlmightyYakob))

#### Authors: 2

- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))

---

# v0.3.54 (Wed Oct 04 2023)

#### 🐛 Bug Fix

- Use correct asset download URL for external services [#1692](https://github.com/dandi/dandi-archive/pull/1692) ([@waxlamp](https://github.com/waxlamp))
- Fix possible race condition in deployment actions [#1679](https://github.com/dandi/dandi-archive/pull/1679) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 2

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))

---

# v0.3.53 (Tue Oct 03 2023)

#### 🐛 Bug Fix

- Increase task timeouts for manifests/asset summaries [#1695](https://github.com/dandi/dandi-archive/pull/1695) ([@danlamanna](https://github.com/danlamanna))

#### Authors: 1

- Dan LaManna ([@danlamanna](https://github.com/danlamanna))

---

# v0.3.52 (Mon Oct 02 2023)

#### 🐛 Bug Fix

- Remove n+1 queries when using full_metadata [#1693](https://github.com/dandi/dandi-archive/pull/1693) ([@danlamanna](https://github.com/danlamanna))
- Fix codespell errors [#1694](https://github.com/dandi/dandi-archive/pull/1694) ([@danlamanna](https://github.com/danlamanna))
- Pin django-storages temporarily [#1691](https://github.com/dandi/dandi-archive/pull/1691) ([@mvandenburgh](https://github.com/mvandenburgh))
- Pin django-allauth to minimum version [#1680](https://github.com/dandi/dandi-archive/pull/1680) ([@mvandenburgh](https://github.com/mvandenburgh))
- Temporary fix for breaking change in `django-allauth` [#1678](https://github.com/dandi/dandi-archive/pull/1678) ([@mvandenburgh](https://github.com/mvandenburgh))
- Design doc for "undelete" feature [#1674](https://github.com/dandi/dandi-archive/pull/1674) ([@mvandenburgh](https://github.com/mvandenburgh) [@yarikoptic](https://github.com/yarikoptic))

#### 🏠 Internal

- [gh-actions](deps): Bump actions/checkout from 3 to 4 [#1676](https://github.com/dandi/dandi-archive/pull/1676) ([@dependabot[bot]](https://github.com/dependabot[bot]))

#### Authors: 4

- [@dependabot[bot]](https://github.com/dependabot[bot])
- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.3.51 (Mon Jul 31 2023)

#### 🐛 Bug Fix

- Add new Django setting to restrict allauth endpoints that are exposed [#1670](https://github.com/dandi/dandi-archive/pull/1670) ([@mvandenburgh](https://github.com/mvandenburgh))
- Rename Version.valid to Version.publishable [#1664](https://github.com/dandi/dandi-archive/pull/1664) ([@danlamanna](https://github.com/danlamanna))

#### Authors: 2

- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.50 (Wed Jul 19 2023)

#### 🐛 Bug Fix

- Don't store dynamic fields in Asset.metadata [#1638](https://github.com/dandi/dandi-archive/pull/1638) ([@AlmightyYakob](https://github.com/AlmightyYakob))

#### Authors: 1

- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))

---

# v0.3.49 (Tue Jul 18 2023)

#### 🐛 Bug Fix

- Set up throttling for validating asset metadata [#1663](https://github.com/dandi/dandi-archive/pull/1663) ([@danlamanna](https://github.com/danlamanna))

#### Authors: 1

- Dan LaManna ([@danlamanna](https://github.com/danlamanna))

---

# v0.3.48 (Tue Jul 18 2023)

#### 🐛 Bug Fix

- Move asset validation to a scheduled task [#1634](https://github.com/dandi/dandi-archive/pull/1634) ([@danlamanna](https://github.com/danlamanna))

#### Authors: 1

- Dan LaManna ([@danlamanna](https://github.com/danlamanna))

---

# v0.3.47 (Mon Jul 17 2023)

#### 🐛 Bug Fix

- Fix typo in footer [#1662](https://github.com/dandi/dandi-archive/pull/1662) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.46 (Mon Jul 17 2023)

:tada: This release contains work from a new contributor! :tada:

Thank you, Jeremy Magland ([@magland](https://github.com/magland)), for all your work!

#### 🐛 Bug Fix

- Unpin dev-only dependencies + disable dependabot [#1661](https://github.com/dandi/dandi-archive/pull/1661) ([@mvandenburgh](https://github.com/mvandenburgh))
- Remove "app" prop from footer [#1652](https://github.com/dandi/dandi-archive/pull/1652) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- adjust neurosift endpoint [#1654](https://github.com/dandi/dandi-archive/pull/1654) ([@magland](https://github.com/magland))
- Assume that browser can play any "video/" content type. [#1627](https://github.com/dandi/dandi-archive/pull/1627) ([@yarikoptic](https://github.com/yarikoptic) [@waxlamp](https://github.com/waxlamp))
- Adding neurosift to external services [#1647](https://github.com/dandi/dandi-archive/pull/1647) ([@satra](https://github.com/satra))
- Minor tuneups to footer [#1651](https://github.com/dandi/dandi-archive/pull/1651) ([@yarikoptic](https://github.com/yarikoptic) [@waxlamp](https://github.com/waxlamp))
- Atomically delete dandiset and its versions [#1642](https://github.com/dandi/dandi-archive/pull/1642) ([@danlamanna](https://github.com/danlamanna))
- Consolidate two DB queries into one [#1635](https://github.com/dandi/dandi-archive/pull/1635) ([@mvandenburgh](https://github.com/mvandenburgh))

#### 🏠 Internal

- Bump types-setuptools from 67.8.0.0 to 68.0.0.0 [#1636](https://github.com/dandi/dandi-archive/pull/1636) ([@dependabot[bot]](https://github.com/dependabot[bot]))
- Bump mypy from 1.3.0 to 1.4.1 [#1637](https://github.com/dandi/dandi-archive/pull/1637) ([@dependabot[bot]](https://github.com/dependabot[bot]))

#### Authors: 8

- [@dependabot[bot]](https://github.com/dependabot[bot])
- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Jeremy Magland ([@magland](https://github.com/magland))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))
- Satrajit Ghosh ([@satra](https://github.com/satra))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.3.45 (Mon Jun 26 2023)

#### 🐛 Bug Fix

- Update VJSF/ajv dependencies, refactor VJSF component to use `<script setup>` [#1599](https://github.com/dandi/dandi-archive/pull/1599) ([@mvandenburgh](https://github.com/mvandenburgh))
- Remove excess rows to fix responsive view of stats bar [#1633](https://github.com/dandi/dandi-archive/pull/1633) ([@marySalvi](https://github.com/marySalvi))
- add scrollIntoView for UI tests [#1632](https://github.com/dandi/dandi-archive/pull/1632) ([@marySalvi](https://github.com/marySalvi))

#### Authors: 2

- Mary Salvi ([@marySalvi](https://github.com/marySalvi))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.44 (Mon Jun 19 2023)

#### 🐛 Bug Fix

- Prevent race condition during zarr ingestion [#1630](https://github.com/dandi/dandi-archive/pull/1630) ([@danlamanna](https://github.com/danlamanna))

#### Authors: 1

- Dan LaManna ([@danlamanna](https://github.com/danlamanna))

---

# v0.3.43 (Mon Jun 19 2023)

#### 🐛 Bug Fix

- Add app prop to footer [#1622](https://github.com/dandi/dandi-archive/pull/1622) ([@marySalvi](https://github.com/marySalvi))
- Limit aggregate asset summaries to valid assets [#1629](https://github.com/dandi/dandi-archive/pull/1629) ([@danlamanna](https://github.com/danlamanna))
- Fix user approval workflow [#1621](https://github.com/dandi/dandi-archive/pull/1621) ([@waxlamp](https://github.com/waxlamp))

#### Authors: 3

- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Mary Salvi ([@marySalvi](https://github.com/marySalvi))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))

---

# v0.3.42 (Thu Jun 15 2023)

#### 🐛 Bug Fix

- Improve validation error display [#1579](https://github.com/dandi/dandi-archive/pull/1579) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Rename e2e test package [#1624](https://github.com/dandi/dandi-archive/pull/1624) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 2

- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.41 (Wed Jun 14 2023)

#### 🐛 Bug Fix

- Add schedule for processing new S3 log files [#1620](https://github.com/dandi/dandi-archive/pull/1620) ([@danlamanna](https://github.com/danlamanna))

#### Authors: 1

- Dan LaManna ([@danlamanna](https://github.com/danlamanna))

---

# v0.3.40 (Tue Jun 06 2023)

#### 🐛 Bug Fix

- Serve pure JSON from /server-info frontend endpoint [#1607](https://github.com/dandi/dandi-archive/pull/1607) ([@waxlamp](https://github.com/waxlamp))

#### Authors: 1

- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))

---

# v0.3.39 (Tue Jun 06 2023)

#### 🐛 Bug Fix

- Bump flake8-bugbear from 23.5.9 to 23.6.5 [#1615](https://github.com/dandi/dandi-archive/pull/1615) ([@dependabot[bot]](https://github.com/dependabot[bot]))
- Add concurrency=1 worker dyno for processing S3 logs [#1614](https://github.com/dandi/dandi-archive/pull/1614) ([@danlamanna](https://github.com/danlamanna))
- Load search results on page load [#1613](https://github.com/dandi/dandi-archive/pull/1613) ([@mvandenburgh](https://github.com/mvandenburgh))
- Refresh search view concurrently [#1612](https://github.com/dandi/dandi-archive/pull/1612) ([@danlamanna](https://github.com/danlamanna))
- Fix search UI for smaller screens [#1610](https://github.com/dandi/dandi-archive/pull/1610) ([@mvandenburgh](https://github.com/mvandenburgh))
- New Dandiset Search Interface [#1598](https://github.com/dandi/dandi-archive/pull/1598) ([@danlamanna](https://github.com/danlamanna) [@mvandenburgh](https://github.com/mvandenburgh))
- Avoid instantiating classes in `swagger_auto_schema` when possible [#1608](https://github.com/dandi/dandi-archive/pull/1608) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 3

- [@dependabot[bot]](https://github.com/dependabot[bot])
- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.38 (Fri May 26 2023)

#### 🐛 Bug Fix

- Fix S3 log file processing [#1605](https://github.com/dandi/dandi-archive/pull/1605) ([@danlamanna](https://github.com/danlamanna))

#### Authors: 1

- Dan LaManna ([@danlamanna](https://github.com/danlamanna))

---

# v0.3.37 (Tue May 23 2023)

#### 🐛 Bug Fix

- Fix URL to the dandi archive repo [#1594](https://github.com/dandi/dandi-archive/pull/1594) ([@yarikoptic](https://github.com/yarikoptic))
- Fix GUI linting warnings [#1590](https://github.com/dandi/dandi-archive/pull/1590) ([@AlmightyYakob](https://github.com/AlmightyYakob))

#### Authors: 2

- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.3.36 (Tue May 23 2023)

#### 🐛 Bug Fix

- Temporarily disable s3 log file processing [#1604](https://github.com/dandi/dandi-archive/pull/1604) ([@danlamanna](https://github.com/danlamanna))
- Update caniuse browserslist DB [#1600](https://github.com/dandi/dandi-archive/pull/1600) ([@mvandenburgh](https://github.com/mvandenburgh))
- Pin `django-minio-storage` [#1597](https://github.com/dandi/dandi-archive/pull/1597) ([@mvandenburgh](https://github.com/mvandenburgh))
- Make deploy workflow names more consistent [#1596](https://github.com/dandi/dandi-archive/pull/1596) ([@mvandenburgh](https://github.com/mvandenburgh))
- Update vuetify + heroku runtime [#1589](https://github.com/dandi/dandi-archive/pull/1589) ([@mvandenburgh](https://github.com/mvandenburgh))

#### 🏠 Internal

- Bump types-setuptools from 67.7.0.0 to 67.8.0.0 [#1602](https://github.com/dandi/dandi-archive/pull/1602) ([@dependabot[bot]](https://github.com/dependabot[bot]))
- Bump flake8-bugbear from 23.3.12 to 23.5.9 [#1591](https://github.com/dandi/dandi-archive/pull/1591) ([@dependabot[bot]](https://github.com/dependabot[bot]))
- Bump mypy from 1.2.0 to 1.3.0 [#1592](https://github.com/dandi/dandi-archive/pull/1592) ([@dependabot[bot]](https://github.com/dependabot[bot]))

#### Authors: 3

- [@dependabot[bot]](https://github.com/dependabot[bot])
- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.35 (Mon May 15 2023)

#### 🐛 Bug Fix

- Add download count tracking to asset blobs [#1570](https://github.com/dandi/dandi-archive/pull/1570) ([@danlamanna](https://github.com/danlamanna))

#### Authors: 1

- Dan LaManna ([@danlamanna](https://github.com/danlamanna))

---

# v0.3.34 (Mon May 08 2023)

#### 🐛 Bug Fix

- Add celery argument logging [#1588](https://github.com/dandi/dandi-archive/pull/1588) ([@danlamanna](https://github.com/danlamanna))

#### 🏠 Internal

- Bump django-stubs from 1.16.0 to 4.2.0 [#1587](https://github.com/dandi/dandi-archive/pull/1587) ([@dependabot[bot]](https://github.com/dependabot[bot]))
- Bump djangorestframework-stubs from 1.10.0 to 3.14.0 [#1586](https://github.com/dandi/dandi-archive/pull/1586) ([@dependabot[bot]](https://github.com/dependabot[bot]))

#### Authors: 2

- [@dependabot[bot]](https://github.com/dependabot[bot])
- Dan LaManna ([@danlamanna](https://github.com/danlamanna))

---

# v0.3.33 (Thu Apr 27 2023)

#### 🐛 Bug Fix

- Bump types-setuptools from 67.6.0.0 to 67.7.0.0 [#1580](https://github.com/dandi/dandi-archive/pull/1580) ([@dependabot[bot]](https://github.com/dependabot[bot]))
- Restore metadata editing [#1584](https://github.com/dandi/dandi-archive/pull/1584) ([@mvandenburgh](https://github.com/mvandenburgh))
- Call `clearInterval` after `setInterval` when needed [#1583](https://github.com/dandi/dandi-archive/pull/1583) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 2

- [@dependabot[bot]](https://github.com/dependabot[bot])
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.32 (Tue Apr 25 2023)

#### 🐛 Bug Fix

- Temporarily disable metadata editing [#1582](https://github.com/dandi/dandi-archive/pull/1582) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.31 (Mon Apr 17 2023)

#### 🐛 Bug Fix

- Temporarily disable meditor local storage restore [#1575](https://github.com/dandi/dandi-archive/pull/1575) ([@mvandenburgh](https://github.com/mvandenburgh))
- Fix flaky version string test [#1572](https://github.com/dandi/dandi-archive/pull/1572) ([@danlamanna](https://github.com/danlamanna))

#### 🏠 Internal

- [gh-actions](deps): Bump actions/add-to-project from 0.4.0 to 0.5.0 [#1558](https://github.com/dandi/dandi-archive/pull/1558) ([@dependabot[bot]](https://github.com/dependabot[bot]))

#### Authors: 3

- [@dependabot[bot]](https://github.com/dependabot[bot])
- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.30 (Tue Apr 11 2023)

#### 🐛 Bug Fix

- Add github username + profile link to UI [#1504](https://github.com/dandi/dandi-archive/pull/1504) ([@mvandenburgh](https://github.com/mvandenburgh))
- Embed glob-derived regex inside a ^/$ pair [#1566](https://github.com/dandi/dandi-archive/pull/1566) ([@waxlamp](https://github.com/waxlamp))
- Render description field as markdown [#1568](https://github.com/dandi/dandi-archive/pull/1568) ([@waxlamp](https://github.com/waxlamp))
- Add license info to dandiset creation page + do a style overhaul [#1554](https://github.com/dandi/dandi-archive/pull/1554) ([@waxlamp](https://github.com/waxlamp))
- Optimize dandiset/versions and dandiset/versions/info endpoints [#1548](https://github.com/dandi/dandi-archive/pull/1548) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Fix typo [#1564](https://github.com/dandi/dandi-archive/pull/1564) ([@waxlamp](https://github.com/waxlamp))
- Enable inline view of assets [#1534](https://github.com/dandi/dandi-archive/pull/1534) ([@waxlamp](https://github.com/waxlamp))

#### 🏠 Internal

- Bump mypy from 1.1.1 to 1.2.0 [#1569](https://github.com/dandi/dandi-archive/pull/1569) ([@dependabot[bot]](https://github.com/dependabot[bot]))

#### Authors: 4

- [@dependabot[bot]](https://github.com/dependabot[bot])
- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))

---

# v0.3.29 (Wed Mar 29 2023)

#### 🐛 Bug Fix

- Boost minimal client version to be 0.51.0 since needed for fresh dandischema [#1542](https://github.com/dandi/dandi-archive/pull/1542) ([@yarikoptic](https://github.com/yarikoptic))
- Test for "Licenses" DLP element in E2E test [#1511](https://github.com/dandi/dandi-archive/pull/1511) ([@mvandenburgh](https://github.com/mvandenburgh))
- Update Vue to 2.7.14 [#1549](https://github.com/dandi/dandi-archive/pull/1549) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 2

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.3.28 (Tue Mar 21 2023)

#### 🐛 Bug Fix

- Add doi share link and update styles [#1539](https://github.com/dandi/dandi-archive/pull/1539) ([@marySalvi](https://github.com/marySalvi))

#### Authors: 1

- Mary Salvi ([@marySalvi](https://github.com/marySalvi))

---

# v0.3.27 (Tue Mar 21 2023)

#### 🐛 Bug Fix

- Improve the admin interface for versions [#1547](https://github.com/dandi/dandi-archive/pull/1547) ([@danlamanna](https://github.com/danlamanna))
- Always force ingestion from zarr admin action [#1541](https://github.com/dandi/dandi-archive/pull/1541) ([@AlmightyYakob](https://github.com/AlmightyYakob))

#### 🏠 Internal

- Bump djangorestframework-stubs from 1.9.1 to 1.10.0 [#1544](https://github.com/dandi/dandi-archive/pull/1544) ([@dependabot[bot]](https://github.com/dependabot[bot]))
- Bump django-stubs from 1.15.0 to 1.16.0 [#1543](https://github.com/dandi/dandi-archive/pull/1543) ([@dependabot[bot]](https://github.com/dependabot[bot]))

#### Authors: 3

- [@dependabot[bot]](https://github.com/dependabot[bot])
- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))

---

# v0.3.26 (Fri Mar 17 2023)

:tada: This release contains work from a new contributor! :tada:

Thank you, Mary Salvi ([@marySalvi](https://github.com/marySalvi)), for all your work!

#### 🐛 Bug Fix

- Log response body if DOI request fails [#1540](https://github.com/dandi/dandi-archive/pull/1540) ([@mvandenburgh](https://github.com/mvandenburgh))
- Add button to copy id to clipboard [#1523](https://github.com/dandi/dandi-archive/pull/1523) ([@marySalvi](https://github.com/marySalvi))
- Update runtime.txt version [#1538](https://github.com/dandi/dandi-archive/pull/1538) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 2

- Mary Salvi ([@marySalvi](https://github.com/marySalvi))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.25 (Thu Mar 16 2023)

#### 🐛 Bug Fix

- update dandischema to recover validation version 0.6.3 [#1537](https://github.com/dandi/dandi-archive/pull/1537) ([@satra](https://github.com/satra))

#### Authors: 1

- Satrajit Ghosh ([@satra](https://github.com/satra))

---

# v0.3.24 (Wed Mar 15 2023)

#### 🐛 Bug Fix

- Handle zarrs properly in asset metadata validation [#1515](https://github.com/dandi/dandi-archive/pull/1515) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Add eslint rule enforcing the use of `import type` [#1519](https://github.com/dandi/dandi-archive/pull/1519) ([@mvandenburgh](https://github.com/mvandenburgh))
- Update development instructions [#1528](https://github.com/dandi/dandi-archive/pull/1528) ([@mvandenburgh](https://github.com/mvandenburgh))

#### 🏠 Internal

- Bump djangorestframework-stubs from 1.8.0 to 1.9.1 [#1507](https://github.com/dandi/dandi-archive/pull/1507) ([@dependabot[bot]](https://github.com/dependabot[bot]))
- Bump mypy from 1.0.0 to 1.1.1 [#1531](https://github.com/dandi/dandi-archive/pull/1531) ([@dependabot[bot]](https://github.com/dependabot[bot]))
- Bump types-setuptools from 67.5.0.0 to 67.6.0.0 [#1532](https://github.com/dandi/dandi-archive/pull/1532) ([@dependabot[bot]](https://github.com/dependabot[bot]))
- Bump flake8-bugbear from 23.2.13 to 23.3.12 [#1533](https://github.com/dandi/dandi-archive/pull/1533) ([@dependabot[bot]](https://github.com/dependabot[bot]))

#### Authors: 3

- [@dependabot[bot]](https://github.com/dependabot[bot])
- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.23 (Fri Mar 10 2023)

#### 🐛 Bug Fix

- Fix zarr publish error bug [#1529](https://github.com/dandi/dandi-archive/pull/1529) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.22 (Fri Mar 10 2023)

#### 🐛 Bug Fix

- Empty PR to cut a release [#1527](https://github.com/dandi/dandi-archive/pull/1527) ([@mvandenburgh](https://github.com/mvandenburgh))
- Boost dandischema to 0.8.0 to get newer DANDI_SCHEMA_VERSION 0.6.4 supported [#1524](https://github.com/dandi/dandi-archive/pull/1524) ([@yarikoptic](https://github.com/yarikoptic))
- Disable the publish button when Zarrs are contained in the Dandiset [#1517](https://github.com/dandi/dandi-archive/pull/1517) ([@waxlamp](https://github.com/waxlamp))
- Improve codespell configuration [#1518](https://github.com/dandi/dandi-archive/pull/1518) ([@danlamanna](https://github.com/danlamanna))
- Optimize Dandiset List Endpoint [#1503](https://github.com/dandi/dandi-archive/pull/1503) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- codespell: ignore `CHANGELOG.md` [#1512](https://github.com/dandi/dandi-archive/pull/1512) ([@mvandenburgh](https://github.com/mvandenburgh))

#### 🏠 Internal

- Bump types-setuptools from 67.3.0.1 to 67.5.0.0 [#1522](https://github.com/dandi/dandi-archive/pull/1522) ([@dependabot[bot]](https://github.com/dependabot[bot]))
- Bump django-stubs from 1.14.0 to 1.15.0 [#1509](https://github.com/dandi/dandi-archive/pull/1509) ([@dependabot[bot]](https://github.com/dependabot[bot]))

#### Authors: 6

- [@dependabot[bot]](https://github.com/dependabot[bot])
- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.3.21 (Tue Feb 28 2023)

#### 🐛 Bug Fix

- Fix license type, improve type annotation [#1510](https://github.com/dandi/dandi-archive/pull/1510) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.20 (Mon Feb 27 2023)

#### 🐛 Bug Fix

- Only allow selecting one license on create dandiset page [#1505](https://github.com/dandi/dandi-archive/pull/1505) ([@mvandenburgh](https://github.com/mvandenburgh))
- Fix mispelling of "occurred" [#1506](https://github.com/dandi/dandi-archive/pull/1506) ([@AlmightyYakob](https://github.com/AlmightyYakob))

#### Authors: 2

- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.19 (Fri Feb 24 2023)

#### 🐛 Bug Fix

- Use `import type` syntax in CreateDandisetView [#1502](https://github.com/dandi/dandi-archive/pull/1502) ([@mvandenburgh](https://github.com/mvandenburgh))
- CreateDandisetView: Fix max length for name/description [#1501](https://github.com/dandi/dandi-archive/pull/1501) ([@mvandenburgh](https://github.com/mvandenburgh))
- Add script to download papertrail logs [#1421](https://github.com/dandi/dandi-archive/pull/1421) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Add codespell config and fix typos to `tox -e lint`, fix typos, add custom dictionary (not enabling for now) [#1466](https://github.com/dandi/dandi-archive/pull/1466) ([@yarikoptic](https://github.com/yarikoptic))
- fix: allow for listing organizations as contributors [#1499](https://github.com/dandi/dandi-archive/pull/1499) ([@satra](https://github.com/satra))

#### Authors: 4

- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Satrajit Ghosh ([@satra](https://github.com/satra))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.3.18 (Wed Feb 22 2023)

#### 🐛 Bug Fix

- Release with auto [#1500](https://github.com/dandi/dandi-archive/pull/1500) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Rename field in zarr file request to `base64md5` for clarity [#1498](https://github.com/dandi/dandi-archive/pull/1498) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Add back md5 to zarr object url signing [#1497](https://github.com/dandi/dandi-archive/pull/1497) ([@danlamanna](https://github.com/danlamanna) [@AlmightyYakob](https://github.com/AlmightyYakob))
- Remove overly aggressive exception handling [#1490](https://github.com/dandi/dandi-archive/pull/1490) ([@danlamanna](https://github.com/danlamanna))

#### 🏠 Internal

- Bump types-setuptools from 67.2.0.1 to 67.3.0.1 [#1495](https://github.com/dandi/dandi-archive/pull/1495) ([@dependabot[bot]](https://github.com/dependabot[bot]))
- Pin to Node 16 in CI [#1496](https://github.com/dandi/dandi-archive/pull/1496) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 4

- [@dependabot[bot]](https://github.com/dependabot[bot])
- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.17 (Tue Feb 21 2023)

#### 🐛 Bug Fix

- Display error message for invalid dandiset URL [#1454](https://github.com/dandi/dandi-archive/pull/1454) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.16 (Thu Feb 16 2023)

#### 🐛 Bug Fix

- Add locking to asset update/delete at API level [#1485](https://github.com/dandi/dandi-archive/pull/1485) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Convert `OverviewTab` component to `<script setup>` [#1453](https://github.com/dandi/dandi-archive/pull/1453) ([@mvandenburgh](https://github.com/mvandenburgh))
- Stop trimming characters off of test zarr paths [#1493](https://github.com/dandi/dandi-archive/pull/1493) ([@danlamanna](https://github.com/danlamanna))

#### 🏠 Internal

- Bump flake8-bugbear from 23.1.20 to 23.2.13 [#1492](https://github.com/dandi/dandi-archive/pull/1492) ([@dependabot[bot]](https://github.com/dependabot[bot]))
- Bump types-setuptools from 67.1.0.0 to 67.2.0.1 [#1491](https://github.com/dandi/dandi-archive/pull/1491) ([@dependabot[bot]](https://github.com/dependabot[bot]))

#### Authors: 4

- [@dependabot[bot]](https://github.com/dependabot[bot])
- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.15 (Mon Feb 13 2023)

#### 🐛 Bug Fix

- Skip computing assets summary for invalid assets [#1489](https://github.com/dandi/dandi-archive/pull/1489) ([@danlamanna](https://github.com/danlamanna))

#### Authors: 1

- Dan LaManna ([@danlamanna](https://github.com/danlamanna))

---

# v0.3.14 (Fri Feb 10 2023)

#### 🐛 Bug Fix

- Implement new zarr upload process [#1448](https://github.com/dandi/dandi-archive/pull/1448) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Simplify zarr upload process design [#1464](https://github.com/dandi/dandi-archive/pull/1464) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Upgrade black to 23.1.0 [#1465](https://github.com/dandi/dandi-archive/pull/1465) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Restore published version emulation for validation purposes [#1459](https://github.com/dandi/dandi-archive/pull/1459) ([@danlamanna](https://github.com/danlamanna))
- Update DLP UI for asynchronous assets summary [#1452](https://github.com/dandi/dandi-archive/pull/1452) ([@mvandenburgh](https://github.com/mvandenburgh))
- Compute asset summary asynchronously for draft versions [#1431](https://github.com/dandi/dandi-archive/pull/1431) ([@danlamanna](https://github.com/danlamanna))

#### 🏠 Internal

- Bump types-setuptools from 65.7.0.1 to 67.1.0.0 [#1467](https://github.com/dandi/dandi-archive/pull/1467) ([@dependabot[bot]](https://github.com/dependabot[bot]))
- Bump mypy from 0.991 to 1.0.0 [#1468](https://github.com/dandi/dandi-archive/pull/1468) ([@dependabot[bot]](https://github.com/dependabot[bot]))
- Bump flake8-docstrings from 1.6.0 to 1.7.0 [#1458](https://github.com/dandi/dandi-archive/pull/1458) ([@dependabot[bot]](https://github.com/dependabot[bot]))
- Bump django-stubs from 1.13.1 to 1.14.0 [#1457](https://github.com/dandi/dandi-archive/pull/1457) ([@dependabot[bot]](https://github.com/dependabot[bot]))

#### Authors: 4

- [@dependabot[bot]](https://github.com/dependabot[bot])
- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.13 (Fri Jan 27 2023)

#### 🐛 Bug Fix

- Add 12 hour cache to stats endpoint [#1416](https://github.com/dandi/dandi-archive/pull/1416) ([@AlmightyYakob](https://github.com/AlmightyYakob))

#### 🏠 Internal

- Bump flake8-bugbear from 22.12.6 to 23.1.20 [#1446](https://github.com/dandi/dandi-archive/pull/1446) ([@dependabot[bot]](https://github.com/dependabot[bot]))

#### Authors: 2

- [@dependabot[bot]](https://github.com/dependabot[bot])
- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))

---

# v0.3.12 (Mon Jan 23 2023)

#### 🐛 Bug Fix

- Require rejection reason when rejecting a new user [#1443](https://github.com/dandi/dandi-archive/pull/1443) ([@mvandenburgh](https://github.com/mvandenburgh))
- Fix dependabot ignore types [#1445](https://github.com/dandi/dandi-archive/pull/1445) ([@danlamanna](https://github.com/danlamanna))

#### Authors: 2

- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.11 (Mon Jan 23 2023)

#### 🐛 Bug Fix

- Fix publishing UI bug [#1442](https://github.com/dandi/dandi-archive/pull/1442) ([@mvandenburgh](https://github.com/mvandenburgh))
- Allow deleting embargoed dandisets [#1438](https://github.com/dandi/dandi-archive/pull/1438) ([@danlamanna](https://github.com/danlamanna))
- ENH: explicitly describe both cases of not allowed dandiset deletion [#1433](https://github.com/dandi/dandi-archive/pull/1433) ([@yarikoptic](https://github.com/yarikoptic))
- Fix dependabot ignore type [#1437](https://github.com/dandi/dandi-archive/pull/1437) ([@danlamanna](https://github.com/danlamanna))
- Add design doc for Zarr upload process simplification [#1415](https://github.com/dandi/dandi-archive/pull/1415) ([@waxlamp](https://github.com/waxlamp) [@AlmightyYakob](https://github.com/AlmightyYakob))

#### 🏠 Internal

- Bump types-setuptools from 65.6.0.3 to 65.7.0.1 [#1434](https://github.com/dandi/dandi-archive/pull/1434) ([@dependabot[bot]](https://github.com/dependabot[bot]))
- Bump boto3-stubs[s3] from 1.26.46 to 1.26.50 [#1435](https://github.com/dandi/dandi-archive/pull/1435) ([@dependabot[bot]](https://github.com/dependabot[bot]))

#### Authors: 6

- [@dependabot[bot]](https://github.com/dependabot[bot])
- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.3.10 (Wed Jan 11 2023)

#### 🐛 Bug Fix

- Remove use of checksum files in zarr ingestion [#1395](https://github.com/dandi/dandi-archive/pull/1395) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Add request timeouts for S3 storage [#1428](https://github.com/dandi/dandi-archive/pull/1428) ([@danlamanna](https://github.com/danlamanna))
- Add MINIO_STORAGE_MEDIA_URL to docker-compose-native config [#1427](https://github.com/dandi/dandi-archive/pull/1427) ([@danlamanna](https://github.com/danlamanna))

#### 🏠 Internal

- Bump boto3-stubs[s3] from 1.26.41 to 1.26.46 [#1429](https://github.com/dandi/dandi-archive/pull/1429) ([@dependabot[bot]](https://github.com/dependabot[bot]))
- Bump types-setuptools from 65.6.0.2 to 65.6.0.3 [#1430](https://github.com/dandi/dandi-archive/pull/1430) ([@dependabot[bot]](https://github.com/dependabot[bot]))

#### Authors: 3

- [@dependabot[bot]](https://github.com/dependabot[bot])
- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))

---

# v0.3.9 (Mon Jan 09 2023)

#### 🐛 Bug Fix

- Reduce sentry performance sample rate for asset download [#1417](https://github.com/dandi/dandi-archive/pull/1417) ([@danlamanna](https://github.com/danlamanna))
- Ignore patch updates for dependabot [#1426](https://github.com/dandi/dandi-archive/pull/1426) ([@danlamanna](https://github.com/danlamanna))
- Add more detailed logging to development postgres [#1414](https://github.com/dandi/dandi-archive/pull/1414) ([@danlamanna](https://github.com/danlamanna))
- Remove redundant call to update_asset_paths [#1413](https://github.com/dandi/dandi-archive/pull/1413) ([@danlamanna](https://github.com/danlamanna))

#### 🏠 Internal

- Bump flake8-isort from 5.0.3 to 6.0.0 [#1419](https://github.com/dandi/dandi-archive/pull/1419) ([@dependabot[bot]](https://github.com/dependabot[bot]))
- Bump boto3-stubs[s3] from 1.26.32 to 1.26.41 [#1422](https://github.com/dandi/dandi-archive/pull/1422) ([@dependabot[bot]](https://github.com/dependabot[bot]))
- Bump flake8-black from 0.3.5 to 0.3.6 [#1420](https://github.com/dandi/dandi-archive/pull/1420) ([@dependabot[bot]](https://github.com/dependabot[bot]))
- Bump pep8-naming from 0.13.2 to 0.13.3 [#1410](https://github.com/dandi/dandi-archive/pull/1410) ([@dependabot[bot]](https://github.com/dependabot[bot]))

#### Authors: 2

- [@dependabot[bot]](https://github.com/dependabot[bot])
- Dan LaManna ([@danlamanna](https://github.com/danlamanna))

---

# v0.3.8 (Mon Dec 19 2022)

#### 🐛 Bug Fix

- Use flat file listing in zarr file browser [#1394](https://github.com/dandi/dandi-archive/pull/1394) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Use proper syntax for only locking ZarrArchive table [#1398](https://github.com/dandi/dandi-archive/pull/1398) ([@danlamanna](https://github.com/danlamanna))
- Simplify ingest_zarr_archive task [#1391](https://github.com/dandi/dandi-archive/pull/1391) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Batch bulk_create calls in publish [#1400](https://github.com/dandi/dandi-archive/pull/1400) ([@mvandenburgh](https://github.com/mvandenburgh))
- Remove special casing of backups2datalad user agent [#1397](https://github.com/dandi/dandi-archive/pull/1397) ([@danlamanna](https://github.com/danlamanna))
- Optimize `ingest_zarr_archive` task [#1387](https://github.com/dandi/dandi-archive/pull/1387) ([@AlmightyYakob](https://github.com/AlmightyYakob))

#### 🏠 Internal

- Bump flake8 from 5.0.4 to 6.0.0 [#1404](https://github.com/dandi/dandi-archive/pull/1404) ([@dependabot[bot]](https://github.com/dependabot[bot]))
- Bump flake8-quotes from 3.3.1 to 3.3.2 [#1409](https://github.com/dandi/dandi-archive/pull/1409) ([@dependabot[bot]](https://github.com/dependabot[bot]))
- Bump mypy from 0.982 to 0.991 [#1407](https://github.com/dandi/dandi-archive/pull/1407) ([@dependabot[bot]](https://github.com/dependabot[bot]))
- Bump boto3-stubs[s3] from 1.26.27 to 1.26.32 [#1405](https://github.com/dandi/dandi-archive/pull/1405) ([@dependabot[bot]](https://github.com/dependabot[bot]))
- Manage CI dependencies with dependabot [#1402](https://github.com/dandi/dandi-archive/pull/1402) ([@mvandenburgh](https://github.com/mvandenburgh))
- [gh-actions](deps): Bump actions/add-to-project from 0.3.0 to 0.4.0 [#1382](https://github.com/dandi/dandi-archive/pull/1382) ([@dependabot[bot]](https://github.com/dependabot[bot]))
- Move asset publishing to publish service [#1399](https://github.com/dandi/dandi-archive/pull/1399) ([@mvandenburgh](https://github.com/mvandenburgh))
- Specify `requests` as a prod dependency instead of test [#1401](https://github.com/dandi/dandi-archive/pull/1401) ([@mvandenburgh](https://github.com/mvandenburgh))
- Optimize memory use in publish service [#1376](https://github.com/dandi/dandi-archive/pull/1376) ([@mvandenburgh](https://github.com/mvandenburgh))
- Move metadata validation tasks into the service layer [#1379](https://github.com/dandi/dandi-archive/pull/1379) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 4

- [@dependabot[bot]](https://github.com/dependabot[bot])
- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.7 (Wed Dec 07 2022)

#### 🐛 Bug Fix

- Refresh asset object before validating it after creation [#1393](https://github.com/dandi/dandi-archive/pull/1393) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.6 (Tue Dec 06 2022)

#### 🐛 Bug Fix

- Always clear checksum files during zarr ingestion [#1390](https://github.com/dandi/dandi-archive/pull/1390) ([@AlmightyYakob](https://github.com/AlmightyYakob))

#### 📝 Documentation

- dandi-archive web app readme edit [#1386](https://github.com/dandi/dandi-archive/pull/1386) ([@melster1010](https://github.com/melster1010))

#### Authors: 2

- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Mary Elise Dedicke ([@melster1010](https://github.com/melster1010))

---

# v0.3.5 (Wed Nov 30 2022)

#### 🐛 Bug Fix

- Prevent locking dandisets during zarr upload [#1385](https://github.com/dandi/dandi-archive/pull/1385) ([@danlamanna](https://github.com/danlamanna))

#### Authors: 1

- Dan LaManna ([@danlamanna](https://github.com/danlamanna))

---

# v0.3.4 (Tue Nov 29 2022)

#### 🐛 Bug Fix

- Add file upload instructions to file browser UI [#1342](https://github.com/dandi/dandi-archive/pull/1342) ([@mvandenburgh](https://github.com/mvandenburgh))

#### 🏠 Internal

- Convert FileBrowser component to <script setup> [#1340](https://github.com/dandi/dandi-archive/pull/1340) ([@mvandenburgh](https://github.com/mvandenburgh))
- Convert `Meditor.vue` to `<script setup>` [#1303](https://github.com/dandi/dandi-archive/pull/1303) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.3 (Tue Nov 29 2022)

#### 🐛 Bug Fix

- Fix publishing being allowed for pending assets [#1383](https://github.com/dandi/dandi-archive/pull/1383) ([@mvandenburgh](https://github.com/mvandenburgh))
- Temporarily pin flake8 [#1380](https://github.com/dandi/dandi-archive/pull/1380) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.3.2 (Mon Nov 21 2022)

#### 🐛 Bug Fix

- Fix file browser bug [#1374](https://github.com/dandi/dandi-archive/pull/1374) ([@mvandenburgh](https://github.com/mvandenburgh))
- After Asset metadata validation, update Version timestamp with single query [#1373](https://github.com/dandi/dandi-archive/pull/1373) ([@mvandenburgh](https://github.com/mvandenburgh))
- Improved pagination design in file browser [#1311](https://github.com/dandi/dandi-archive/pull/1311) ([@mvandenburgh](https://github.com/mvandenburgh))
- add zarr validator service [#1370](https://github.com/dandi/dandi-archive/pull/1370) ([@satra](https://github.com/satra))
- Add embargo service [#1367](https://github.com/dandi/dandi-archive/pull/1367) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Properly handle conflicting asset paths [#1368](https://github.com/dandi/dandi-archive/pull/1368) ([@AlmightyYakob](https://github.com/AlmightyYakob))

#### 🏠 Internal

- Convert `DandisetLandingView` to `<script setup>`, use `vue-router` composable [#1316](https://github.com/dandi/dandi-archive/pull/1316) ([@mvandenburgh](https://github.com/mvandenburgh))
- Internal publishing service [#1363](https://github.com/dandi/dandi-archive/pull/1363) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 3

- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Satrajit Ghosh ([@satra](https://github.com/satra))

---

# v0.3.1 (Tue Nov 15 2022)

#### 🐛 Bug Fix

- Save draft versions during asset metadata validation [#1366](https://github.com/dandi/dandi-archive/pull/1366) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Refactor asset create/update/delete [#1352](https://github.com/dandi/dandi-archive/pull/1352) ([@danlamanna](https://github.com/danlamanna))
- Add YouTube channel to approved/registered emails [#1305](https://github.com/dandi/dandi-archive/pull/1305) ([@yarikoptic](https://github.com/yarikoptic))

#### 📝 Documentation

- dandi-archive readme edit [#1357](https://github.com/dandi/dandi-archive/pull/1357) ([@melster1010](https://github.com/melster1010))

#### 🧪 Tests

- Separate backend CI into separate jobs [#1360](https://github.com/dandi/dandi-archive/pull/1360) ([@mvandenburgh](https://github.com/mvandenburgh))
- Pin mypy [#1359](https://github.com/dandi/dandi-archive/pull/1359) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 5

- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Mary Elise Dedicke ([@melster1010](https://github.com/melster1010))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.3.0 (Mon Nov 07 2022)

#### 🚀 Enhancement

- [gh-actions](deps): Bump actions/add-to-project from 0.0.3 to 0.3.0 [#1331](https://github.com/dandi/dandi-archive/pull/1331) ([@dependabot[bot]](https://github.com/dependabot[bot]))

#### 🐛 Bug Fix

- Add tqdm to asset path version ingestion [#1358](https://github.com/dandi/dandi-archive/pull/1358) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Fix oauth client error [#1354](https://github.com/dandi/dandi-archive/pull/1354) ([@mvandenburgh](https://github.com/mvandenburgh))
- Make asset paths operations idempotent [#1351](https://github.com/dandi/dandi-archive/pull/1351) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Delete unused management command import_dandisets.py [#1335](https://github.com/dandi/dandi-archive/pull/1335) ([@danlamanna](https://github.com/danlamanna))
- Optimize version/zarr asset path ingestion [#1343](https://github.com/dandi/dandi-archive/pull/1343) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Add Dandi exception classes [#1337](https://github.com/dandi/dandi-archive/pull/1337) ([@danlamanna](https://github.com/danlamanna))
- Disable APPROVE button if user is already approved [#1348](https://github.com/dandi/dandi-archive/pull/1348) ([@waxlamp](https://github.com/waxlamp))
- Fix dandiset deletion when containing zarrs [#1345](https://github.com/dandi/dandi-archive/pull/1345) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Fix asset update/deletion when associated with zarr [#1338](https://github.com/dandi/dandi-archive/pull/1338) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Optimize Asset Paths [#1312](https://github.com/dandi/dandi-archive/pull/1312) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Wait until after publish transaction commits to create DOI [#1330](https://github.com/dandi/dandi-archive/pull/1330) ([@mvandenburgh](https://github.com/mvandenburgh))
- Revert "[gh-actions](deps): Bump actions/add-to-project from 0.0.3 to 0.3.0" [#1327](https://github.com/dandi/dandi-archive/pull/1327) ([@mvandenburgh](https://github.com/mvandenburgh))
- Restore DLP loading bar, add skeleton loader [#1315](https://github.com/dandi/dandi-archive/pull/1315) ([@mvandenburgh](https://github.com/mvandenburgh))
- Remove vague TODO comment [#1288](https://github.com/dandi/dandi-archive/pull/1288) ([@danlamanna](https://github.com/danlamanna))
- Prevent deletion of dandisets currently being published [#1323](https://github.com/dandi/dandi-archive/pull/1323) ([@mvandenburgh](https://github.com/mvandenburgh))
- Render error message in UI when uncaught exception happens [#1320](https://github.com/dandi/dandi-archive/pull/1320) ([@mvandenburgh](https://github.com/mvandenburgh))

#### 🏠 Internal

- Fix mypy errors in `api/admin.py` [#1333](https://github.com/dandi/dandi-archive/pull/1333) ([@mvandenburgh](https://github.com/mvandenburgh))
- [gh-actions](deps): Bump actions/add-to-project from 0.0.3 to 0.3.0 [#1325](https://github.com/dandi/dandi-archive/pull/1325) ([@dependabot[bot]](https://github.com/dependabot[bot]))
- Update GitHub Actions action versions [#1324](https://github.com/dandi/dandi-archive/pull/1324) ([@jwodder](https://github.com/jwodder))

#### 🧪 Tests

- Disable pulling of all Docker images from Docker Hub [#1339](https://github.com/dandi/dandi-archive/pull/1339) ([@jwodder](https://github.com/jwodder))

#### Authors: 6

- [@dependabot[bot]](https://github.com/dependabot[bot])
- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- John T. Wodder II ([@jwodder](https://github.com/jwodder))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))

---

# v0.2.54 (Tue Oct 11 2022)

#### 🐛 Bug Fix

- Fix 401 errors from `/versions/` endpoint being reported to sentry [#1321](https://github.com/dandi/dandi-archive/pull/1321) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.2.53 (Thu Oct 06 2022)

#### 🐛 Bug Fix

- Prevent double-publishing [#1006](https://github.com/dandi/dandi-archive/pull/1006) ([@mvandenburgh](https://github.com/mvandenburgh))

#### 🧪 Tests

- Add additional waits to account E2E test [#1310](https://github.com/dandi/dandi-archive/pull/1310) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.2.52 (Tue Oct 04 2022)

#### 🐛 Bug Fix

- Update frontend to use new query parameter for version listing endpoint [#1309](https://github.com/dandi/dandi-archive/pull/1309) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.2.51 (Tue Oct 04 2022)

#### 🐛 Bug Fix

- Use `django_filters` instead of DRF for Version viewset filtering [#1308](https://github.com/dandi/dandi-archive/pull/1308) ([@mvandenburgh](https://github.com/mvandenburgh))
- Unpin minio docker image and update env var names [#1307](https://github.com/dandi/dandi-archive/pull/1307) ([@mvandenburgh](https://github.com/mvandenburgh))
- Update e2e test dependencies [#1306](https://github.com/dandi/dandi-archive/pull/1306) ([@mvandenburgh](https://github.com/mvandenburgh))
- Convert dandiset search test to jest/puppeteer, remove pyppeteer config from project [#1300](https://github.com/dandi/dandi-archive/pull/1300) ([@mvandenburgh](https://github.com/mvandenburgh))
- Disable save button in Meditor if no changes have been made [#1302](https://github.com/dandi/dandi-archive/pull/1302) ([@mvandenburgh](https://github.com/mvandenburgh))
- Include rejection reason in rejected user email [#1301](https://github.com/dandi/dandi-archive/pull/1301) ([@mvandenburgh](https://github.com/mvandenburgh))
- Increase time limit for write_manifest_files [#1299](https://github.com/dandi/dandi-archive/pull/1299) ([@danlamanna](https://github.com/danlamanna))
- Fix missing spacing for validation error UI when logged out [#1297](https://github.com/dandi/dandi-archive/pull/1297) ([@mvandenburgh](https://github.com/mvandenburgh))
- Rename file without a trailing space [#1298](https://github.com/dandi/dandi-archive/pull/1298) ([@waxlamp](https://github.com/waxlamp))
- Replace pyppeteer test for cookie behavior with puppeteer test [#1295](https://github.com/dandi/dandi-archive/pull/1295) ([@mvandenburgh](https://github.com/mvandenburgh))
- Turn on mypy for `zarr/admin.py` and `zarr/views/` + fix type errors [#1296](https://github.com/dandi/dandi-archive/pull/1296) ([@mvandenburgh](https://github.com/mvandenburgh))
- Refactor dandiset create/delete methods [#1292](https://github.com/dandi/dandi-archive/pull/1292) ([@danlamanna](https://github.com/danlamanna))
- Revert "Temporarily pin DRF" [#1293](https://github.com/dandi/dandi-archive/pull/1293) ([@danlamanna](https://github.com/danlamanna))
- Convert `DandisetPublish.vue` to `<script setup>` [#1283](https://github.com/dandi/dandi-archive/pull/1283) ([@mvandenburgh](https://github.com/mvandenburgh))
- Make misc fixes to the dandiset ownership email [#1279](https://github.com/dandi/dandi-archive/pull/1279) ([@danlamanna](https://github.com/danlamanna))
- Fix link to download help handbook page [#1289](https://github.com/dandi/dandi-archive/pull/1289) ([@mvandenburgh](https://github.com/mvandenburgh))
- Allow for using django core exceptions with DRF [#1290](https://github.com/dandi/dandi-archive/pull/1290) ([@danlamanna](https://github.com/danlamanna))
- Use `exact` prop consistently [#1285](https://github.com/dandi/dandi-archive/pull/1285) ([@waxlamp](https://github.com/waxlamp))
- Temporarily pin DRF [#1291](https://github.com/dandi/dandi-archive/pull/1291) ([@danlamanna](https://github.com/danlamanna))
- Turn off autoescaping for text/plain emails [#1276](https://github.com/dandi/dandi-archive/pull/1276) ([@danlamanna](https://github.com/danlamanna))

#### Authors: 3

- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))

---

# v0.2.50 (Thu Sep 22 2022)

#### 🐛 Bug Fix

- Fix asset unembargo method [#1282](https://github.com/dandi/dandi-archive/pull/1282) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Remove `-s` and `-v` flags from CLI integration test invocation [#1287](https://github.com/dandi/dandi-archive/pull/1287) ([@mvandenburgh](https://github.com/mvandenburgh))
- Don't revalidate version metadata on PUT unless it has changed [#1280](https://github.com/dandi/dandi-archive/pull/1280) ([@mvandenburgh](https://github.com/mvandenburgh))
- Fix `useRouter()` sentry error [#1284](https://github.com/dandi/dandi-archive/pull/1284) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 2

- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.2.49 (Mon Sep 19 2022)

#### 🐛 Bug Fix

- Enable sentry performance for frontend [#1270](https://github.com/dandi/dandi-archive/pull/1270) ([@mvandenburgh](https://github.com/mvandenburgh))
- Only suppress 4xx errors in pinia action [#1281](https://github.com/dandi/dandi-archive/pull/1281) ([@mvandenburgh](https://github.com/mvandenburgh))
- Improve edge cases around email greetings [#1275](https://github.com/dandi/dandi-archive/pull/1275) ([@danlamanna](https://github.com/danlamanna))

#### Authors: 2

- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.2.48 (Tue Sep 13 2022)

#### 🐛 Bug Fix

- Add social accounts to user admin page [#1274](https://github.com/dandi/dandi-archive/pull/1274) ([@danlamanna](https://github.com/danlamanna))
- Use direct foreign keys with django-guardian [#1273](https://github.com/dandi/dandi-archive/pull/1273) ([@danlamanna](https://github.com/danlamanna))
- Make Dandiset sorting account for zarr files [#1271](https://github.com/dandi/dandi-archive/pull/1271) ([@danlamanna](https://github.com/danlamanna))

#### Authors: 1

- Dan LaManna ([@danlamanna](https://github.com/danlamanna))

---

# v0.2.47 (Thu Sep 08 2022)

#### 🐛 Bug Fix

- Fix vuetify console error on DLP [#1269](https://github.com/dandi/dandi-archive/pull/1269) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.2.46 (Thu Sep 08 2022)

#### 🐛 Bug Fix

- Update Sentry frontend configuration and report error logs [#1268](https://github.com/dandi/dandi-archive/pull/1268) ([@mvandenburgh](https://github.com/mvandenburgh))
- Fix display of validation errors when there's no associated field [#1266](https://github.com/dandi/dandi-archive/pull/1266) ([@danlamanna](https://github.com/danlamanna))
- Migrate Vuex store to Pinia [#1265](https://github.com/dandi/dandi-archive/pull/1265) ([@mvandenburgh](https://github.com/mvandenburgh))
- Fix missing package error when first using docker-compose setup [#1158](https://github.com/dandi/dandi-archive/pull/1158) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Remove unnecessary conditional check for schemaVersion [#1257](https://github.com/dandi/dandi-archive/pull/1257) ([@danlamanna](https://github.com/danlamanna))
- Convert some vue components to `<script setup>` [#1263](https://github.com/dandi/dandi-archive/pull/1263) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 3

- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.2.45 (Thu Sep 01 2022)

#### 🐛 Bug Fix

- Upgrade frontend to Vue 2.7 [#1258](https://github.com/dandi/dandi-archive/pull/1258) ([@mvandenburgh](https://github.com/mvandenburgh))
- Replace `vue-type-check` with `vue-tsc` [#1259](https://github.com/dandi/dandi-archive/pull/1259) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.2.44 (Wed Aug 31 2022)

#### 🐛 Bug Fix

- Create django app for zarr functionality [#1256](https://github.com/dandi/dandi-archive/pull/1256) ([@danlamanna](https://github.com/danlamanna))
- Rearrange file structure [#1255](https://github.com/dandi/dandi-archive/pull/1255) ([@mvandenburgh](https://github.com/mvandenburgh))
- Remove TODO about Django Sites [#1254](https://github.com/dandi/dandi-archive/pull/1254) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 2

- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.2.43 (Thu Aug 25 2022)

#### 🐛 Bug Fix

- Update assets path pagination [#1253](https://github.com/dandi/dandi-archive/pull/1253) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Fix type errors in `mail.py` [#1250](https://github.com/dandi/dandi-archive/pull/1250) ([@mvandenburgh](https://github.com/mvandenburgh))
- Remove `management/` directory from excluded mypy files [#1252](https://github.com/dandi/dandi-archive/pull/1252) ([@mvandenburgh](https://github.com/mvandenburgh))
- Remove `migrations/` from excluded mypy files [#1251](https://github.com/dandi/dandi-archive/pull/1251) ([@mvandenburgh](https://github.com/mvandenburgh))
- Fix asset list performance issue [#1222](https://github.com/dandi/dandi-archive/pull/1222) ([@danlamanna](https://github.com/danlamanna))
- Fix `target-version` for black [#1249](https://github.com/dandi/dandi-archive/pull/1249) ([@mvandenburgh](https://github.com/mvandenburgh))
- Require Python 3.10 [#1247](https://github.com/dandi/dandi-archive/pull/1247) ([@mvandenburgh](https://github.com/mvandenburgh))
- Fix type errors in `models` [#1246](https://github.com/dandi/dandi-archive/pull/1246) ([@mvandenburgh](https://github.com/mvandenburgh))
- Fix type errors in `tasks` [#1244](https://github.com/dandi/dandi-archive/pull/1244) ([@mvandenburgh](https://github.com/mvandenburgh))
- Update s3-file-field dependency [#1241](https://github.com/dandi/dandi-archive/pull/1241) ([@danlamanna](https://github.com/danlamanna))
- Clean up storage layer [#1238](https://github.com/dandi/dandi-archive/pull/1238) ([@danlamanna](https://github.com/danlamanna))
- Optimize zarr list endpoint [#1220](https://github.com/dandi/dandi-archive/pull/1220) ([@AlmightyYakob](https://github.com/AlmightyYakob) [@danlamanna](https://github.com/danlamanna))
- Remove unused dependency httpx [#1240](https://github.com/dandi/dandi-archive/pull/1240) ([@danlamanna](https://github.com/danlamanna))
- Fix incorrect type hints [#1231](https://github.com/dandi/dandi-archive/pull/1231) ([@mvandenburgh](https://github.com/mvandenburgh))
- Require metadata/asset schemaVersion [#1199](https://github.com/dandi/dandi-archive/pull/1199) ([@danlamanna](https://github.com/danlamanna))
- Fix zarr viewer [#1236](https://github.com/dandi/dandi-archive/pull/1236) ([@mvandenburgh](https://github.com/mvandenburgh))
- Add external viewer for NGFF files [#1067](https://github.com/dandi/dandi-archive/pull/1067) ([@mvandenburgh](https://github.com/mvandenburgh))
- Revert "Pin flake8 version" [#1233](https://github.com/dandi/dandi-archive/pull/1233) ([@mvandenburgh](https://github.com/mvandenburgh))
- changes in ShareDialog: using inline style [#828](https://github.com/dandi/dandi-archive/pull/828) ([@djarecka](https://github.com/djarecka) [@mvandenburgh](https://github.com/mvandenburgh))
- DOC: add DLP abbreviation to initiate Abbreviations in DEVELOPMENT.md [#1224](https://github.com/dandi/dandi-archive/pull/1224) ([@yarikoptic](https://github.com/yarikoptic))
- De-Duplicate API calls in DLP [#1208](https://github.com/dandi/dandi-archive/pull/1208) ([@DeepikaGhodki](https://github.com/DeepikaGhodki))
- Use tuples for Admin model actions and inlines [#1229](https://github.com/dandi/dandi-archive/pull/1229) ([@AlmightyYakob](https://github.com/AlmightyYakob))

#### 🧪 Tests

- Configure mypy [#1243](https://github.com/dandi/dandi-archive/pull/1243) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 6

- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Deepika Ghodki ([@DeepikaGhodki](https://github.com/DeepikaGhodki))
- Dorota Jarecka ([@djarecka](https://github.com/djarecka))
- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.2.42 (Wed Aug 03 2022)

:tada: This release contains work from a new contributor! :tada:

Thank you, Deepika Ghodki ([@DeepikaGhodki](https://github.com/DeepikaGhodki)), for all your work!

#### 🐛 Bug Fix

- Use an ordered QuerySet in Zarr viewset [#1202](https://github.com/dandi/dandi-archive/pull/1202) ([@waxlamp](https://github.com/waxlamp))
- Navigation buttons on landing page [#1172](https://github.com/dandi/dandi-archive/pull/1172) ([@DeepikaGhodki](https://github.com/DeepikaGhodki))
- Pin flake8 version [#1226](https://github.com/dandi/dandi-archive/pull/1226) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Remove flake8 linting rule [#1223](https://github.com/dandi/dandi-archive/pull/1223) ([@danlamanna](https://github.com/danlamanna))
- Escape . in regex for EXTERNAL_SERVICES [#1191](https://github.com/dandi/dandi-archive/pull/1191) ([@yarikoptic](https://github.com/yarikoptic))
- Add "/server-info/" frontend endpoint in development builds [#1190](https://github.com/dandi/dandi-archive/pull/1190) ([@waxlamp](https://github.com/waxlamp))

#### Authors: 5

- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Deepika Ghodki ([@DeepikaGhodki](https://github.com/DeepikaGhodki))
- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.2.41 (Wed Jul 27 2022)

:tada: This release contains work from a new contributor! :tada:

Thank you, Deepika Ghodki ([@DeepikaGhodki](https://github.com/DeepikaGhodki)), for all your work!

#### 🐛 Bug Fix

- Add metadata flag for asset listing [#1216](https://github.com/dandi/dandi-archive/pull/1216) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Handle forbidden characters in asset path [#1201](https://github.com/dandi/dandi-archive/pull/1201) ([@DeepikaGhodki](https://github.com/DeepikaGhodki))
- Add memray dev deps to setup.py [#1143](https://github.com/dandi/dandi-archive/pull/1143) ([@AlmightyYakob](https://github.com/AlmightyYakob))

#### 📝 Documentation

- Update Zarr design doc for changes to checksum format [#1175](https://github.com/dandi/dandi-archive/pull/1175) ([@jwodder](https://github.com/jwodder))

#### Authors: 3

- Deepika Ghodki ([@DeepikaGhodki](https://github.com/DeepikaGhodki))
- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- John T. Wodder II ([@jwodder](https://github.com/jwodder))

---

# v0.2.40 (Tue Jul 26 2022)

#### 🐛 Bug Fix

- Improve sentry configuration [#1215](https://github.com/dandi/dandi-archive/pull/1215) ([@danlamanna](https://github.com/danlamanna))
- Prefer social account data over direct user data [#1140](https://github.com/dandi/dandi-archive/pull/1140) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Present dialog if attempting to remove self from dandiset [#1125](https://github.com/dandi/dandi-archive/pull/1125) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Unpin `numpy` dependency in CLI tests [#1212](https://github.com/dandi/dandi-archive/pull/1212) ([@mvandenburgh](https://github.com/mvandenburgh))
- Fix bug in `import_dandisets` script [#1211](https://github.com/dandi/dandi-archive/pull/1211) ([@mvandenburgh](https://github.com/mvandenburgh))
- Fix partial filename from paths_prefix [#591](https://github.com/dandi/dandi-archive/pull/591) ([@AlmightyYakob](https://github.com/AlmightyYakob))

#### 🏠 Internal

- Properly include "data packages" in project [#1114](https://github.com/dandi/dandi-archive/pull/1114) ([@jwodder](https://github.com/jwodder))

#### Authors: 4

- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- John T. Wodder II ([@jwodder](https://github.com/jwodder))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.2.39 (Fri Jul 22 2022)

#### 🐛 Bug Fix

- Enable Sentry performance tracking [#1209](https://github.com/dandi/dandi-archive/pull/1209) ([@danlamanna](https://github.com/danlamanna))
- Add ngff rename script as a management command [#1120](https://github.com/dandi/dandi-archive/pull/1120) ([@mvandenburgh](https://github.com/mvandenburgh))
- Add publish "checklist" [#1122](https://github.com/dandi/dandi-archive/pull/1122) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 2

- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.2.38 (Tue Jul 19 2022)

#### 🐛 Bug Fix

- Improve manifest file writing performance [#1184](https://github.com/dandi/dandi-archive/pull/1184) ([@danlamanna](https://github.com/danlamanna))
- Add time limits to celery tasks [#1187](https://github.com/dandi/dandi-archive/pull/1187) ([@danlamanna](https://github.com/danlamanna))
- boost copyright to 2022 from 2019 [#893](https://github.com/dandi/dandi-archive/pull/893) ([@yarikoptic](https://github.com/yarikoptic))

#### Authors: 2

- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.2.37 (Tue Jul 12 2022)

#### 🐛 Bug Fix

- Fix admin search fields [#1185](https://github.com/dandi/dandi-archive/pull/1185) ([@danlamanna](https://github.com/danlamanna))
- Fix flaky e2e test [#1178](https://github.com/dandi/dandi-archive/pull/1178) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 2

- Dan LaManna ([@danlamanna](https://github.com/danlamanna))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.2.36 (Mon Jul 11 2022)

#### 🐛 Bug Fix

- Write manifest files after committing transaction [#1176](https://github.com/dandi/dandi-archive/pull/1176) ([@danlamanna](https://github.com/danlamanna))
- Upgrade django-composed-configuration [#1174](https://github.com/dandi/dandi-archive/pull/1174) ([@danlamanna](https://github.com/danlamanna))
- Allow longer zarr blob names [#1173](https://github.com/dandi/dandi-archive/pull/1173) ([@danlamanna](https://github.com/danlamanna))

#### Authors: 1

- Dan LaManna ([@danlamanna](https://github.com/danlamanna))

---

# v0.2.35 (Mon Jul 11 2022)

:tada: This release contains work from a new contributor! :tada:

Thank you, Dan LaManna ([@danlamanna](https://github.com/danlamanna)), for all your work!

#### 🐛 Bug Fix

- Improve load times of admin pages [#1169](https://github.com/dandi/dandi-archive/pull/1169) ([@danlamanna](https://github.com/danlamanna))

#### Authors: 1

- Dan LaManna ([@danlamanna](https://github.com/danlamanna))

---

# v0.2.34 (Thu Jul 07 2022)

#### 🐛 Bug Fix

- Fix more memory issues in tasks [#1161](https://github.com/dandi/dandi-archive/pull/1161) ([@mvandenburgh](https://github.com/mvandenburgh))
- Use iteration instead of recursion in `import_dandisets` script [#1150](https://github.com/dandi/dandi-archive/pull/1150) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.2.33 (Thu Jul 07 2022)

#### 🐛 Bug Fix

- Fix race condition in sha256 calculation [#1164](https://github.com/dandi/dandi-archive/pull/1164) ([@mvandenburgh](https://github.com/mvandenburgh) [@AlmightyYakob](https://github.com/AlmightyYakob))

#### Authors: 2

- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.2.32 (Wed Jul 06 2022)

#### 🐛 Bug Fix

- Optimize dandiset list endpoint [#1134](https://github.com/dandi/dandi-archive/pull/1134) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- adding license field to the create dandiset page [#839](https://github.com/dandi/dandi-archive/pull/839) ([@djarecka](https://github.com/djarecka) [@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 3

- Dorota Jarecka ([@djarecka](https://github.com/djarecka))
- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.2.31 (Tue Jul 05 2022)

#### 🐛 Bug Fix

- Fix excessive memory usage in asset summary calculation [#1159](https://github.com/dandi/dandi-archive/pull/1159) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.2.30 (Fri Jul 01 2022)

#### 🐛 Bug Fix

- Fix missing zarr_id in `cancel_zarr_upload` [#1154](https://github.com/dandi/dandi-archive/pull/1154) ([@AlmightyYakob](https://github.com/AlmightyYakob))

#### Authors: 1

- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))

---

# v0.2.29 (Fri Jul 01 2022)

#### 🐛 Bug Fix

- Use `logging.info` for user errors instead of `logging.error` [#1152](https://github.com/dandi/dandi-archive/pull/1152) ([@mvandenburgh](https://github.com/mvandenburgh))
- Add support for cloning assets to `import_dandisets` script [#1131](https://github.com/dandi/dandi-archive/pull/1131) ([@mvandenburgh](https://github.com/mvandenburgh))
- Sort user search results [#1146](https://github.com/dandi/dandi-archive/pull/1146) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.2.28 (Thu Jun 30 2022)

#### 🐛 Bug Fix

- Revert "Add verbose logging to `ingest_zarr_archive` task" [#1133](https://github.com/dandi/dandi-archive/pull/1133) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.2.27 (Wed Jun 29 2022)

#### 🐛 Bug Fix

- Optimize loop in checksum task [#1139](https://github.com/dandi/dandi-archive/pull/1139) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.2.26 (Mon Jun 27 2022)

#### 🐛 Bug Fix

- Fix broken search bar [#1121](https://github.com/dandi/dandi-archive/pull/1121) ([@mvandenburgh](https://github.com/mvandenburgh))
- Restrict user search [#1124](https://github.com/dandi/dandi-archive/pull/1124) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Add timeout to gunicorn in heroku [#1127](https://github.com/dandi/dandi-archive/pull/1127) ([@mvandenburgh](https://github.com/mvandenburgh))
- Use QuerySet.iterator in asset paths endpoint [#1126](https://github.com/dandi/dandi-archive/pull/1126) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 2

- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.2.25 (Wed Jun 22 2022)

#### 🐛 Bug Fix

- Add verbose logging to `ingest_zarr_archive` task [#1128](https://github.com/dandi/dandi-archive/pull/1128) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.2.24 (Tue Jun 21 2022)

#### 🐛 Bug Fix

- Fix improper escaping of glob parameter, remove regex search [#1062](https://github.com/dandi/dandi-archive/pull/1062) ([@mvandenburgh](https://github.com/mvandenburgh))
- ENH: increase page size from 25 to 100 [#1107](https://github.com/dandi/dandi-archive/pull/1107) ([@yarikoptic](https://github.com/yarikoptic))

#### Authors: 2

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.2.23 (Thu May 12 2022)

#### ⚠️ Pushed to `master`

- Empty commit without markers to skip ci to see if release would be released on netlify ([@yarikoptic](https://github.com/yarikoptic))

#### 🏠 Internal

- BF: provide custom commit message without token to skip the beat [#1101](https://github.com/dandi/dandi-archive/pull/1101) ([@yarikoptic](https://github.com/yarikoptic))

#### Authors: 1

- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.2.22 (Thu May 12 2022)

#### 🏠 Internal

- BF: production-deploy - add "needs" dependency within update-release-branch [#1099](https://github.com/dandi/dandi-archive/pull/1099) ([@yarikoptic](https://github.com/yarikoptic))

#### Authors: 1

- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.2.21 (Wed May 11 2022)

#### 🐛 Bug Fix

- checking the validation status, new attempt [#1097](https://github.com/dandi/dandi-archive/pull/1097) ([@djarecka](https://github.com/djarecka))
- Fix opening Meditor when clicking on "Fix Issues" in the list of dandiset metadata issues [#1088](https://github.com/dandi/dandi-archive/pull/1088) ([@djarecka](https://github.com/djarecka))
- BF(workaround): to avoid crash for user lacking metadata - return INCOMPLETE [#1086](https://github.com/dandi/dandi-archive/pull/1086) ([@yarikoptic](https://github.com/yarikoptic))
- Remove EmbargoedZarrArchive since not supported [#1077](https://github.com/dandi/dandi-archive/pull/1077) ([@yarikoptic](https://github.com/yarikoptic))
- TST: added a test and tune up to factories to ensure that zarr size is computed [#1077](https://github.com/dandi/dandi-archive/pull/1077) ([@yarikoptic](https://github.com/yarikoptic))
- BF: add {Embragoed,}ZarrArchive sizes into total_size compute [#1077](https://github.com/dandi/dandi-archive/pull/1077) ([@yarikoptic](https://github.com/yarikoptic))
- RF: avoid code duplication while considering two types of *AssetBlobs [#1077](https://github.com/dandi/dandi-archive/pull/1077) ([@yarikoptic](https://github.com/yarikoptic))

#### 📝 Documentation

- BF DOC(incomplete): /zarr/.../ingest has 204 not 200 response [#1087](https://github.com/dandi/dandi-archive/pull/1087) ([@yarikoptic](https://github.com/yarikoptic))
- Extend docs with information about devel env [#1084](https://github.com/dandi/dandi-archive/pull/1084) ([@yarikoptic](https://github.com/yarikoptic))

#### Authors: 2

- Dorota Jarecka ([@djarecka](https://github.com/djarecka))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.2.20 (Thu May 05 2022)

#### 🐛 Bug Fix

- Empty commit to cut a release [#1082](https://github.com/dandi/dandi-archive/pull/1082) ([@yarikoptic](https://github.com/yarikoptic))
- Boost dandischema and DANDI_SCHEMA_VERSION [#1074](https://github.com/dandi/dandi-archive/pull/1074) ([@yarikoptic](https://github.com/yarikoptic) [@AlmightyYakob](https://github.com/AlmightyYakob))
- Remove erroneous select_for_update and update tests to use transactions [#1066](https://github.com/dandi/dandi-archive/pull/1066) ([@AlmightyYakob](https://github.com/AlmightyYakob))

#### Authors: 2

- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# v0.2.19 (Fri Apr 29 2022)

#### 🐛 Bug Fix

- Deploy to heroku with Heroku CLI directly [#1075](https://github.com/dandi/dandi-archive/pull/1075) ([@AlmightyYakob](https://github.com/AlmightyYakob))

#### Authors: 1

- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))

---

# v0.2.18 (Fri Apr 29 2022)

#### 🐛 Bug Fix

- Fix version in `/api/info/` [#1054](https://github.com/dandi/dandi-archive/pull/1054) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Fix failing `test_create_dev_dandiset` [#1070](https://github.com/dandi/dandi-archive/pull/1070) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Pin django-oauth-toolkit to 1.x [#1072](https://github.com/dandi/dandi-archive/pull/1072) ([@waxlamp](https://github.com/waxlamp))
- Add garbage collection design doc [#560](https://github.com/dandi/dandi-archive/pull/560) ([@dchiquito](https://github.com/dchiquito))
- Handle missing location query param [#1069](https://github.com/dandi/dandi-archive/pull/1069) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Add actions workflow to auto-add issues to beta project board [#1043](https://github.com/dandi/dandi-archive/pull/1043) ([@waxlamp](https://github.com/waxlamp))
- Misc. Django/Python improvements [#1050](https://github.com/dandi/dandi-archive/pull/1050) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 4

- Daniel Chiquito ([@dchiquito](https://github.com/dchiquito))
- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
- Roni Choudhury ([@waxlamp](https://github.com/waxlamp))

---

# v0.2.17 (Thu Apr 21 2022)

#### 🐛 Bug Fix

- Remove trailing slash in info api url [#1056](https://github.com/dandi/dandi-archive/pull/1056) ([@AlmightyYakob](https://github.com/AlmightyYakob))

#### Authors: 1

- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))

---

# v0.2.16 (Wed Apr 20 2022)

#### 🐛 Bug Fix

- Change `UserMetadata.user` on_delete to `CASCADE` [#1053](https://github.com/dandi/dandi-archive/pull/1053) ([@mvandenburgh](https://github.com/mvandenburgh))
- Add configuration for deploy previews to `netlify.toml` [#1051](https://github.com/dandi/dandi-archive/pull/1051) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.2.15 (Wed Apr 20 2022)

#### 🐛 Bug Fix

- Include `api/` suffix in info endpoint api url [#1049](https://github.com/dandi/dandi-archive/pull/1049) ([@AlmightyYakob](https://github.com/AlmightyYakob))

#### Authors: 1

- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))

---

# v0.2.14 (Wed Apr 20 2022)

#### 🐛 Bug Fix

- Fix incorrect fields in info endpoint [#1046](https://github.com/dandi/dandi-archive/pull/1046) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Select all underlying asset storage fields in asset paths endpoint [#1034](https://github.com/dandi/dandi-archive/pull/1034) ([@AlmightyYakob](https://github.com/AlmightyYakob))

#### Authors: 1

- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))

---

# v0.2.13 (Tue Apr 19 2022)

#### 🐛 Bug Fix

- Empty commit to trigger release [#1042](https://github.com/dandi/dandi-archive/pull/1042) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Add new netlify redirector [#1028](https://github.com/dandi/dandi-archive/pull/1028) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Add netlify plugin and redirection [#1018](https://github.com/dandi/dandi-archive/pull/1018) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Replace use of strip with lstrip [#1041](https://github.com/dandi/dandi-archive/pull/1041) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Add support for glob/regex filtering on `NestedAsset` list endpoint [#1022](https://github.com/dandi/dandi-archive/pull/1022) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 2

- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.2.11 (Mon Apr 18 2022)

#### 🐛 Bug Fix

- Push to heroku directly in update-release-branch.yml [#1038](https://github.com/dandi/dandi-archive/pull/1038) ([@AlmightyYakob](https://github.com/AlmightyYakob))

#### Authors: 1

- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))

---

# v0.2.10 (Mon Apr 18 2022)

#### 🐛 Bug Fix

- Fix disabled Heroku Github integration for staging and production deployment [#1036](https://github.com/dandi/dandi-archive/pull/1036) ([@AlmightyYakob](https://github.com/AlmightyYakob))

#### Authors: 1

- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))

---

# v0.2.8 (Fri Apr 15 2022)

#### 🐛 Bug Fix

- Release branch CI [#1033](https://github.com/dandi/dandi-archive/pull/1033) ([@dchiquito](https://github.com/dchiquito) [@AlmightyYakob](https://github.com/AlmightyYakob))
- Deployment design doc [#1024](https://github.com/dandi/dandi-archive/pull/1024) ([@dchiquito](https://github.com/dchiquito) [@dandibot](https://github.com/dandibot))

#### Authors: 3

- Dandi Bot ([@dandibot](https://github.com/dandibot))
- Daniel Chiquito ([@dchiquito](https://github.com/dchiquito))
- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))

---

# v0.2.8 (Thu Apr 14 2022)

#### 🐛 Bug Fix

- Fix responsiveness of v-app-bar [#1014](https://github.com/dandi/dandi-archive/pull/1014) ([@jtomeck](https://github.com/jtomeck) [@mvandenburgh](https://github.com/mvandenburgh))
- Create design doc for replacing Redirector with Netlify [#1017](https://github.com/dandi/dandi-archive/pull/1017) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Add name and dandiset filtering to zarr list endpoint [#1000](https://github.com/dandi/dandi-archive/pull/1000) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Add force argument in `ingest_zarr_archive` [#1010](https://github.com/dandi/dandi-archive/pull/1010) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Use history mode instead of hash mode (remove hash from GUI URL) [#997](https://github.com/dandi/dandi-archive/pull/997) ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Fix Vue lint step in CI [#1015](https://github.com/dandi/dandi-archive/pull/1015) ([@mvandenburgh](https://github.com/mvandenburgh))
- Set up pyppeteer e2e tests [#990](https://github.com/dandi/dandi-archive/pull/990) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 3

- Jacob Nesbitt ([@AlmightyYakob](https://github.com/AlmightyYakob))
- Jared Tomeck ([@jtomeck](https://github.com/jtomeck))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.2.7 (Wed Apr 06 2022)

#### 🐛 Bug Fix

- Remove `models.PROTECT` from `Asset.previous` [#1009](https://github.com/dandi/dandi-archive/pull/1009) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.2.6 (Wed Apr 06 2022)

#### 🐛 Bug Fix

- Fix search bar overflowing offscreen [#1008](https://github.com/dandi/dandi-archive/pull/1008) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.2.5 (Wed Apr 06 2022)

#### 🐛 Bug Fix

- Make checksum_worker responsible for zarr ingest [#1005](https://github.com/dandi/dandi-archive/pull/1005) ([@dchiquito](https://github.com/dchiquito))

#### Authors: 1

- Daniel Chiquito ([@dchiquito](https://github.com/dchiquito))

---

# v0.2.4 (Wed Apr 06 2022)

#### 🐛 Bug Fix

- Handle validation errors when fetching zarr checksums [#1007](https://github.com/dandi/dandi-archive/pull/1007) ([@dchiquito](https://github.com/dchiquito))

#### Authors: 1

- Daniel Chiquito ([@dchiquito](https://github.com/dchiquito))

---

# v0.2.3 (Wed Apr 06 2022)

#### 🐛 Bug Fix

- Bump dandischema to 0.6.0 [#991](https://github.com/dandi/dandi-archive/pull/991) ([@dchiquito](https://github.com/dchiquito))

#### Authors: 1

- Daniel Chiquito ([@dchiquito](https://github.com/dchiquito))

---

# v0.2.2 (Tue Apr 05 2022)

#### 🐛 Bug Fix

- Allow github login with GET request [#999](https://github.com/dandi/dandi-archive/pull/999) ([@mvandenburgh](https://github.com/mvandenburgh))
- Add manifest-worker to Celery in dev environment [#994](https://github.com/dandi/dandi-archive/pull/994) ([@dchiquito](https://github.com/dchiquito))
- Make publishing an atomic operation [#978](https://github.com/dandi/dandi-archive/pull/978) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 2

- Daniel Chiquito ([@dchiquito](https://github.com/dchiquito))
- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.2.1 (Tue Mar 29 2022)

#### 🐛 Bug Fix

- Empty commit to cut a release [#989](https://github.com/dandi/dandi-archive/pull/989) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))

---

# v0.2.0 (Tue Mar 29 2022)

#### 🚀 Enhancement

- Cut a release [#988](https://github.com/dandi/dandi-archive/pull/988) ([@mvandenburgh](https://github.com/mvandenburgh))
- Empty commit to cut a release [#986](https://github.com/dandi/dandi-archive/pull/986) ([@mvandenburgh](https://github.com/mvandenburgh))
- Empty commit to cut release (again) [#984](https://github.com/dandi/dandi-archive/pull/984) ([@mvandenburgh](https://github.com/mvandenburgh))
- Empty commit to cut a release [#982](https://github.com/dandi/dandi-archive/pull/982) ([@mvandenburgh](https://github.com/mvandenburgh))
- Use custom github token for auto release workflow [#979](https://github.com/dandi/dandi-archive/pull/979) ([@mvandenburgh](https://github.com/mvandenburgh))
- Use `intuit/auto` to manage releases [#973](https://github.com/dandi/dandi-archive/pull/973) ([@mvandenburgh](https://github.com/mvandenburgh))

#### 🐛 Bug Fix

- Use PAT when checking out repo in release workflow [#987](https://github.com/dandi/dandi-archive/pull/987) ([@mvandenburgh](https://github.com/mvandenburgh))
- Use dandibot auto token [#981](https://github.com/dandi/dandi-archive/pull/981) ([@mvandenburgh](https://github.com/mvandenburgh))

#### Authors: 1

- Mike VanDenburgh ([@mvandenburgh](https://github.com/mvandenburgh))
