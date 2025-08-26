<template>
  <v-footer class="text-body-2">
    <v-container>
      <CookieBanner />
      <v-row>
        <v-col offset="2">
          &copy; 2019 - 2025 The DANDI Team<br>
          <a
            target="_blank"
            rel="noopener"
            :href="`${dandiDocumentationUrl}/terms-policies/terms/`"
          >Terms</a>
          <v-icon size="x-small">
            mdi-open-in-new
          </v-icon> / <a
            target="_blank"
            rel="noopener"
            :href="`${dandiDocumentationUrl}/terms-policies/policies/`"
          >Policies</a>
          <v-icon size="x-small">
            mdi-open-in-new
          </v-icon> / <a
            target="_blank"
            rel="noopener"
            href="https://github.com/dandi/dandi-archive/blob/master/CODE_OF_CONDUCT.md"
          >Code of Conduct</a>
          <v-icon size="x-small">
            mdi-open-in-new
          </v-icon>
          <br>
          version
          <a
            class="version-link"
            :href="githubLink"
            target="_blank"
            rel="noopener"
          >{{ version }}</a>
        </v-col>
        <v-col>
          Funding / In-Kind Support:<br>
          - <a
            target="_blank"
            rel="noopener"
            href="https://braininitiative.nih.gov/"
          >BRAIN Initiative</a>
          <v-icon size="x-small">
            mdi-open-in-new
          </v-icon> / <a
            target="_blank"
            rel="noopener"
            href="https://www.nimh.nih.gov/index.shtml"
          >NIMH</a>
          <v-icon size="x-small">
            mdi-open-in-new
          </v-icon>
          <br>
          - <a
            target="_blank"
            rel="noopener"
            href="https://registry.opendata.aws/dandiarchive/"
          >AWS Open Dataset</a>
          <v-icon size="x-small">
            mdi-open-in-new
          </v-icon>
          <br>
          - <a
            target="_blank"
            rel="noopener"
            href="https://netlify.com"
          >This site is powered by Netlify</a>
          <v-icon size="x-small">
            mdi-open-in-new
          </v-icon>
        </v-col>
        <v-col>
          Support:<br>
          - <a
            target="_blank"
            rel="noopener"
            href="mailto:help@dandiarchive.org"
          >Send an email</a>
          <v-icon size="x-small">
            mdi-open-in-new
          </v-icon>
          <br>
          - <a
            target="_blank"
            rel="noopener"
            href="https://github.com/dandi/helpdesk/issues/new/choose"
          >File an issue</a>
          <v-icon size="x-small">
            mdi-open-in-new
          </v-icon>
        </v-col>
      </v-row>
    </v-container>
  </v-footer>
</template>

<script setup lang="ts">
import CookieBanner from './CookieBanner.vue';
import { dandiDocumentationUrl } from '@/utils/constants';

const version = import.meta.env.VITE_APP_VERSION;
const githubLink = import.meta.env.VITE_APP_GIT_REVISION ? `https://github.com/dandi/dandi-archive/commit/${import.meta.env.VITE_APP_GIT_REVISION}` : 'https://github.com/dandi/dandi-archive';
</script>

<style scoped>
@media (min-width: 1904px) {
  .container {
    max-width: 1185px;
  }
}

.version-link {
  color: inherit;
}

.version-link:hover {
  text-decoration: underline;
}
</style>
