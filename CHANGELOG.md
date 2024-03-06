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
