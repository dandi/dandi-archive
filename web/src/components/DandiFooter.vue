<template>
  <v-footer class="text-body-2">
    <v-container>
      <!-- <cookie-law theme="blood-orange">
        <div slot="message">
          <span
            v-if="cookiesEnabled()"
          >We use cookies to ensure you get the best experience on
            DANDI.</span>
          <span
            v-else
          >We noticed you're blocking cookies - note that certain aspects of
            the site may not work.</span>
        </div>
      </cookie-law> -->
      <v-row>
        <v-col offset="2">
          &copy; 2019 - 2024 The DANDI Team<br>
          <a
            target="_blank"
            rel="noopener"
            href="https://docs.dandiarchive.org/about/terms/"
          >Terms</a>
          <v-icon size="x-small">
            mdi-open-in-new
          </v-icon> / <a
            target="_blank"
            rel="noopener"
            href="https://docs.dandiarchive.org/about/policies/"
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

<script lang="ts">
import { defineComponent } from 'vue';

import { cookiesEnabled } from '@/rest';

const version = import.meta.env.VITE_APP_VERSION;
const githubLink = import.meta.env.VITE_APP_GIT_REVISION ? `https://github.com/dandi/dandi-archive/commit/${import.meta.env.VITE_APP_GIT_REVISION}` : 'https://github.com/dandi/dandi-archive';

export default defineComponent({
  name: 'DandiFooter',
  setup() {
    return {
      version,
      githubLink,
      cookiesEnabled,
    };
  },
});
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
