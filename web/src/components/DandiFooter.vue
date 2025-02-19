<template>
  <v-footer class="text-body-2">
    <v-container>
      <cookie-law theme="blood-orange">
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
      </cookie-law>
      <v-row>
        <v-col offset="2">
          &copy; 2019 - 2024 The DANDI Team<br>
          &copy; 2024 - 2025 JHU/APL.<br>
          <a
            target="_blank"
            rel="noopener"
            href="https://docs.dandiarchive.org/about/terms/"
          >Terms</a> 
          <v-icon x-small>
            mdi-open-in-new
          </v-icon> / <a
            target="_blank"
            rel="noopener"
            href="https://docs.dandiarchive.org/about/policies/"
          >Policies</a>
          <v-icon x-small>
            mdi-open-in-new
          </v-icon> / <a
            target="_blank"
            rel="noopener"
            href="https://github.com/dandi/dandi-archive/blob/master/CODE_OF_CONDUCT.md"
          >Code of Conduct</a>
          <v-icon x-small>
            mdi-open-in-new
          </v-icon>
          <br>
          <!-- version
          <a
            class="version-link"
            :href="githubLink"
            target="_blank"
            rel="noopener"
          >{{ version }}</a> -->
        </v-col>
        <v-col>
          Funding / In-Kind Support:<br>
          - <a
            target="_blank"
            rel="noopener"
            href="https://braininitiative.nih.gov/"
          >BRAIN Initiative</a>
          <v-icon x-small>
            mdi-open-in-new
          </v-icon> <a
            target="_blank"
            rel="noopener"
            href="https://braininitiative.nih.gov/research/systems-neuroscience/brain-behavior-quantification-and-synchronization-program"
          >BBQS Program</a>
          <v-icon x-small>
            mdi-open-in-new
          </v-icon>
          <br>
          - <a
            target="_blank"
            rel="noopener"
            href="https://aws.amazon.com/opendata/"
          >AWS Open Data</a>
          <!-- TODO: Update to registry link when released for EMBER: https://registry.opendata.aws/XXX/ -->
          <v-icon x-small>
            mdi-open-in-new
          </v-icon>
          <br>
          - <a
            target="_blank"
            rel="noopener"
            href="https://netlify.com"
          >This site is powered by Netlify</a>
          <v-icon x-small>
            mdi-open-in-new
          </v-icon>
          <br>
          - <a
            target="_blank"
            rel="noopener"
            :href="dandiUrl"
          >DANDI</a>
          <v-icon x-small>
            mdi-open-in-new
          </v-icon>
        </v-col>
        <v-col>
          Support:<br>
          - <a
            target="_blank"
            rel="noopener"
            href="mailto:help@emberarchive.org"
          >Send an email</a>
          <v-icon x-small>
            mdi-open-in-new
          </v-icon>
          <br>
          - <a
            target="_blank"
            rel="noopener"
            href="https://github.com/dandi/helpdesk/issues/new/choose"
          >File an issue</a>
          <v-icon x-small>
            mdi-open-in-new
          </v-icon>
        </v-col>
      </v-row>
    </v-container>
  </v-footer>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import CookieLaw from 'vue-cookie-law';

import { dandiUrl, emberHomeUrl, emberGitHubUrl } from '@/utils/constants';
import { cookiesEnabled } from '@/rest';

const version = import.meta.env.VITE_APP_VERSION;
const githubLink = import.meta.env.VITE_APP_GIT_REVISION ? `https://github.com/aplbrain/dandi-archive/commit/${import.meta.env.VITE_APP_GIT_REVISION}` : 'https://github.com/aplbrain/dandi-archive';

export default defineComponent({
  name: 'DandiFooter',
  components: { CookieLaw },
  setup() {
    return {
      dandiUrl,
      emberHomeUrl,
      emberGitHubUrl,
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
