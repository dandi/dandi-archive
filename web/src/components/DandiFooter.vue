<script>
import { copyToClipboard, dandiAboutUrl } from '@/utils';

export default {
  name: 'DandiFooter',
  data: () => ({
    copied: false,
    dandiAboutUrl,
  }),
  computed: {
    version() {
      return process.env.VUE_APP_VERSION;
    },
  },
  methods: {
    versionClick() {
      this.copied = true;
      setTimeout(() => { this.copied = false; }, 1000);
      copyToClipboard(this.version);
    },
  },
};
</script>

<template>
  <v-footer class="text-body-2">
    <v-container>
      <v-row>
        <v-col offset="2">
          &copy; 2020 DANDI<br>
          version
          <v-tooltip
            v-model="copied"
            bottom
            :open-on-hover="false"
          >
            <template #activator="{ on }">
              <a
                class="version-link"
                v-on="on"
                @click="versionClick"
              >{{ version.slice(0, 6) }}</a>
            </template>
            <span>Copied to clipboard!</span>
          </v-tooltip>
        </v-col>
        <v-col>
          Funding:<br>
          - <a
            target="_blank"
            href="https://braininitiative.nih.gov/"
          >BRAIN Initiative</a><br>
          - <a
            target="_blank"
            href="https://www.nimh.nih.gov/index.shtml"
          >NIMH</a><br>
        </v-col>
        <v-col>
          Support:<br>
          - <a
            target="_blank"
            :href="dandiAboutUrl"
          >Dandi Project Homepage</a><br>
          - <a
            target="_blank"
            href="https://github.com/dandi/dandiarchive"
          >Project Github</a> / <a
            target="_blank"
            href="https://github.com/dandi/dandiarchive/issues"
          >Issues</a>
        </v-col>
      </v-row>
    </v-container>
  </v-footer>
</template>

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
