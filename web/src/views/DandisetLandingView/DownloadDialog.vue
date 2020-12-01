<template>
  <v-menu
    offset-y
    :close-on-content-click="false"
    left
    min-width="500"
    max-width="500"
  >
    <template v-slot:activator="{ on }">
      <slot
        name="activator"
        :on="on"
      />
    </template>
    <v-card>
      <v-card-title>
        Download full dandiset
        <v-spacer />
        <v-tooltip right>
          <template v-slot:activator="{ on }">
            <v-btn
              href="https://www.dandiarchive.org/handbook/10_using_dandi/#downloading-from-dandi"
              target="_blank"
              rel="noopener"
              text
            >
              Help
              <v-icon
                color="primary"
                small
                v-on="on"
              >
                mdi-help-circle
              </v-icon>
            </v-btn>
          </template>
          More help on download
        </v-tooltip>
      </v-card-title>
      <v-list class="pa-0">
        <v-list-item dense>
          Use this command in your DANDI CLI
        </v-list-item>
        <v-list-item dense>
          <CopyText
            :text="defaultDownloadText"
            icon-hover-text="Copy command to clipboard"
            dense
            filled
            outlined
          />
        </v-list-item>
        <v-expansion-panels>
          <v-expansion-panel v-if="availableVersions.length > 0">
            <v-expansion-panel-header>
              Download a different version?
            </v-expansion-panel-header>
            <v-expansion-panel-content>
              <v-list class="pa-0">
                <v-list-item dense>
                  <v-radio-group v-model="selectedDownloadOption">
                    <v-radio
                      label="Draft"
                      value="draft"
                    />
                    <v-radio
                      label="Latest version"
                      value="latest"
                    />
                    <v-radio
                      label="Other version"
                      value="other"
                    />
                    <v-select
                      v-if="selectedDownloadOption == 'other'"
                      v-model="selectedVersion"
                      :items="availableVersions"
                      item-text="version"
                      item-value="index"
                      dense
                    />
                  </v-radio-group>
                </v-list-item>
                <v-list-item dense>
                  <CopyText
                    :text="customDownloadText"
                    icon-hover-text="Copy command to clipboard"
                    color="primary"
                    dense
                    outlined
                    filled
                  />
                </v-list-item>
              </v-list>
            </v-expansion-panel-content>
          </v-expansion-panel>
          <v-expansion-panel>
            <v-expansion-panel-header>
              Don't have DANDI CLI?
            </v-expansion-panel-header>
            <v-expansion-panel-content>
              <v-list>
                <v-list-item>
                  Install the Python client (DANDI CLI)
                  in a Python 3.6+ environment using command:
                </v-list-item>
                <v-list-item>
                  <kbd>pip install "dandi>=0.6.0"</kbd>
                </v-list-item>
              </v-list>
            </v-expansion-panel-content>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-list>
    </v-card>
  </v-menu>
</template>
<script>
import { mapState, mapGetters } from 'vuex';
import CopyText from '@/components/CopyText.vue';
import toggles from '@/featureToggle';

function formatDownloadCommand(identifier, version) {
  if (version === 'draft') {
    return `dandi download https://dandiarchive.org/dandiset/${identifier}/draft`;
  }
  if (!version) {
    return `dandi download DANDI:${identifier}`;
  }
  return `dandi download DANDI:${identifier}/${version}`;
}

export default {
  name: 'DownloadDialog',
  components: {
    CopyText,
  },
  data() {
    return {
      selectedDownloadOption: 'draft',
      selectedVersion: 0,
    };
  },
  computed: {
    defaultDownloadText() {
      const { identifier, currentVersion } = this;
      return formatDownloadCommand(identifier, currentVersion);
    },
    customDownloadText() {
      const {
        identifier,
        selectedDownloadOption,
        availableVersions,
        selectedVersion,
      } = this;
      if (selectedDownloadOption === 'draft') {
        return formatDownloadCommand(identifier, 'draft');
      } if (selectedDownloadOption === 'latest') {
        return formatDownloadCommand(identifier);
      } if (selectedDownloadOption === 'other') {
        return formatDownloadCommand(identifier, availableVersions[selectedVersion].version);
      }
      return '';
    },
    availableVersions() {
      return (this.publishedVersions || [])
        .map((version, index) => ({ version: version.version, index }));
    },
    identifier() {
      if (toggles.DJANGO_API) {
        return this.publishDandiset.identifier;
      } else {
        return this.girderDandiset.meta.dandiset.identifier;
      }
    },
    ...mapState('dandiset', {
      girderDandiset: (state) => state.girderDandiset,
      publishDandiset: (state) => state.publishDandiset,
      publishedVersions: (state) => state.versions,
    }),
    ...mapGetters('dandiset', {
      currentVersion: 'version',
    }),
  },
};
</script>
