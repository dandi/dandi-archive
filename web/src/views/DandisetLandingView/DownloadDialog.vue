<template>
  <v-menu
    offset-y
    :close-on-content-click="false"
    left
    min-width="500"
    max-width="500"
  >
    <template #activator="{ on }">
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
          <template #activator="{ on }">
            <v-btn
              href="https://www.dandiarchive.org/handbook/12_download/"
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
          Use this command in your Lincbrain CLI
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
                  in a Python 3.7+ environment using command:
                </v-list-item>
                <v-list-item>
                  <kbd>pip install "dandi>=0.13.0"</kbd>
                </v-list-item>
              </v-list>
            </v-expansion-panel-content>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-list>
    </v-card>
  </v-menu>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue';
import { useDandisetStore } from '@/stores/dandiset';
import CopyText from '@/components/CopyText.vue';

function formatDownloadCommand(identifier: string, version: string): string {
  if (version === 'draft') {
    return `lincbrain download https://lincbrain.org/dandiset/${identifier}/draft`;
  }
  if (!version) {
    return `lincbrain download DANDI:${identifier}`;
  }
  return `lincbrain download DANDI:${identifier}/${version}`;
}

const store = useDandisetStore();

const currentDandiset = computed(() => store.dandiset);
const publishedVersions = computed(() => store.versions);
const currentVersion = computed(() => store.version);

const selectedDownloadOption = ref('draft');
const selectedVersion = ref(0);

const identifier = computed(() => currentDandiset.value?.dandiset.identifier);

const availableVersions = computed(
  () => (publishedVersions.value || [])
    .map((version, index) => ({ version: version.version, index })),
);

const defaultDownloadText = computed(
  () => (identifier.value ? formatDownloadCommand(identifier.value, currentVersion.value) : ''),
);

const customDownloadText = computed(() => {
  if (!identifier.value) {
    return '';
  }
  if (selectedDownloadOption.value === 'draft') {
    return formatDownloadCommand(identifier.value, 'draft');
  } if (selectedDownloadOption.value === 'latest') {
    return formatDownloadCommand(identifier.value, '');
  } if (selectedDownloadOption.value === 'other') {
    return formatDownloadCommand(
      identifier.value,
      availableVersions.value[selectedVersion.value].version,
    );
  }
  return '';
});
</script>
