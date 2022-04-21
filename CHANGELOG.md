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
