<template>
  <v-footer
    class="text-body-2"
    app
  >
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
          &copy; 2019 - 2022 The DANDI Team<br>
          version
          <a
            class="version-link"
            :href="githubLink"
            target="_blank"
            rel="noopener"
          >{{ version }}</a>
        </v-col>
        <v-col>
          Funding:<br>
          - <a
            target="_blank"
            rel="noopener"
            href="https://braininitiative.nih.gov/"
          >BRAIN Initiative</a>
          <v-icon x-small>
            mdi-open-in-new
          </v-icon>
          <br>
          - <a
            target="_blank"
            rel="noopener"
            href="https://www.nimh.nih.gov/index.shtml"
          >NIMH</a>
          <v-icon x-small>
            mdi-open-in-new
          </v-icon>
          <br>
        </v-col>
        <v-col>
          Support:<br>
          - <a
            target="_blank"
            rel="noopener"
            :href="dandiAboutUrl"
          >DANDI Project Homepage</a>
          <v-icon x-small>
            mdi-open-in-new
          </v-icon>
          <br>
          - <a
            target="_blank"
            rel="noopener"
            href="https://github.com/dandi/dandi-archive"
          >Project GitHub</a>
          <v-icon x-small>
            mdi-open-in-new
          </v-icon> / <a
            target="_blank"
            rel="noopener"
            href="https://github.com/dandi/dandi-archive/issues"
          >Issues</a>
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

import { dandiAboutUrl } from '@/utils/constants';
import { cookiesEnabled } from '@/rest';

const version = process.env.VUE_APP_VERSION;
const githubLink = process.env.VUE_APP_GIT_REVISION ? `https://github.com/dandi/dandi-archive/commit/${process.env.VUE_APP_GIT_REVISION}` : 'https://github.com/dandi/dandi-archive';

export default defineComponent({
  name: 'DandiFooter',
  components: { CookieLaw },
  setup() {
    return {
      dandiAboutUrl,
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
