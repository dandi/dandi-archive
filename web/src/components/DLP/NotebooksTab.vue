<template>
  <div v-if="notebooks">
    <v-card
      variant="outlined"
      class="pa-6"
    >
      <v-card-title class="d-flex align-center px-0 pt-0">
        <v-icon
          color="primary"
          class="mr-2"
        >
          mdi-notebook-outline
        </v-icon>
        Notebooks
      </v-card-title>

      <v-card-text class="px-0">
        <p class="text-body-1 mb-4">
          Step-by-step Jupyter notebooks showing how to load and analyze this
          dandiset, organized by the folders they live in on
          <a
            :href="notebooks.siteUrl"
            target="_blank"
            rel="noopener"
          >DANDI Notebooks</a>.
          Open one directly in Google Colab, or run it on your own machine with
          its Docker image where one is available; see the site's
          <a
            :href="notebooks.dockerHelpUrl"
            target="_blank"
            rel="noopener"
          >instructions for running the Docker images</a>.
        </p>

        <template
          v-for="(group, groupIndex) in groupedNotebooks"
          :key="group.key"
        >
          <v-divider
            v-if="groupIndex > 0"
            class="my-4"
          />

          <h3
            v-if="group.segments.length"
            class="text-h6 d-flex align-center flex-wrap ga-1 mb-2"
          >
            <v-icon
              color="primary"
              size="20"
              class="mr-1"
            >
              mdi-folder-outline
            </v-icon>
            <template
              v-for="(segment, i) in group.segments"
              :key="i"
            >
              <v-icon
                v-if="i > 0"
                size="16"
                class="text-medium-emphasis"
              >
                mdi-chevron-right
              </v-icon>
              <span class="text-no-wrap">{{ segment }}</span>
            </template>
          </h3>

          <ul class="notebook-list">
            <li
              v-for="notebook in group.notebooks"
              :key="notebook.path"
            >
              <div class="d-flex align-center flex-wrap ga-2">
                <a
                  :href="notebook.github_url"
                  target="_blank"
                  rel="noopener"
                  class="text-subtitle-1 font-weight-medium text-primary text-decoration-none"
                  :title="notebook.path"
                >
                  {{ notebookTitle(notebook.path) }}
                </a>
                <v-spacer />
                <a
                  v-if="notebook.colab_url"
                  :href="notebook.colab_url"
                  target="_blank"
                  rel="noopener"
                  aria-label="Open in Colab"
                >
                  <img
                    src="https://colab.research.google.com/assets/colab-badge.svg"
                    alt="Open In Colab"
                  >
                </a>
                <v-btn
                  :href="notebook.github_url"
                  target="_blank"
                  rel="noopener"
                  variant="text"
                  size="small"
                  aria-label="View notebook source on GitHub"
                >
                  <v-icon>mdi-github</v-icon>
                  <v-tooltip
                    activator="parent"
                    location="top"
                  >
                    View source on GitHub
                  </v-tooltip>
                </v-btn>
                <v-btn
                  v-if="notebook.docker_command"
                  variant="text"
                  size="small"
                  prepend-icon="mdi-docker"
                  :append-icon="expanded === notebook.path ? 'mdi-chevron-up' : 'mdi-chevron-down'"
                  @click="toggleDocker(notebook.path)"
                >
                  Docker
                  <v-tooltip
                    activator="parent"
                    location="top"
                  >
                    Run locally with Docker
                  </v-tooltip>
                </v-btn>
              </div>

              <v-expand-transition>
                <div v-show="expanded === notebook.path">
                  <div class="d-flex align-center ga-2 mt-1 mb-2">
                    <span class="docker-command">{{ notebook.docker_command }}</span>
                    <v-btn
                      icon
                      size="small"
                      variant="text"
                      class="copy-btn"
                      @click="copyDockerCommand(notebook)"
                    >
                      <v-icon size="small">
                        {{ copied === notebook.path ? 'mdi-check' : 'mdi-content-copy' }}
                      </v-icon>
                      <v-tooltip
                        activator="parent"
                        location="top"
                      >
                        Copy the Docker run command to the clipboard
                      </v-tooltip>
                    </v-btn>
                  </div>
                </div>
              </v-expand-transition>
            </li>
          </ul>
        </template>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import { useDandisetStore } from '@/stores/dandiset';
import { getExampleNotebooks } from '@/utils/notebooks';
import type { DandisetNotebooks, ExampleNotebook } from '@/utils/notebooks';
import type { DandisetMetadata } from '@/types';
import type { ComputedRef, PropType } from 'vue';

defineProps({
  schema: {
    type: Object,
    required: true,
  },
  meta: {
    type: Object as PropType<DandisetMetadata>,
    required: true,
  },
});

interface NotebookGroup {
  key: string;
  segments: string[];
  notebooks: ExampleNotebook[];
}

const store = useDandisetStore();
const currentDandiset = computed(() => store.dandiset);

const notebooks = ref<DandisetNotebooks | null>(null);
const copied = ref<string | null>(null);
const expanded = ref<string | null>(null);

watch(
  () => currentDandiset.value?.dandiset.identifier,
  async (identifier) => {
    const result = identifier ? await getExampleNotebooks(identifier) : null;
    if (currentDandiset.value?.dandiset.identifier === identifier) {
      notebooks.value = result;
    }
  },
  { immediate: true },
);

const groupedNotebooks: ComputedRef<NotebookGroup[]> = computed(() => {
  if (!notebooks.value) {
    return [];
  }
  const identifierPrefix = `${currentDandiset.value?.dandiset.identifier ?? ''}/`;
  const groups = new Map<string, NotebookGroup>();
  for (const notebook of notebooks.value.notebooks) {
    const relativePath = notebook.path.startsWith(identifierPrefix)
      ? notebook.path.slice(identifierPrefix.length)
      : notebook.path;
    const lastSlash = relativePath.lastIndexOf('/');
    const key = lastSlash === -1 ? '' : relativePath.slice(0, lastSlash);
    let group = groups.get(key);
    if (!group) {
      group = {
        key,
        segments: key.split('/').filter(Boolean).map(prettySegment),
        notebooks: [],
      };
      groups.set(key, group);
    }
    group.notebooks.push(notebook);
  }
  return Array.from(groups.values());
});

function prettySegment(segment: string): string {
  return segment.replaceAll('_', ' ');
}

function toggleDocker(path: string) {
  expanded.value = expanded.value === path ? null : path;
}

async function copyDockerCommand(notebook: ExampleNotebook) {
  if (!notebook.docker_command) {
    return;
  }
  try {
    await navigator.clipboard.writeText(notebook.docker_command);
    copied.value = notebook.path;
    window.setTimeout(() => {
      if (copied.value === notebook.path) {
        copied.value = null;
      }
    }, 2000);
  } catch (err) {
    console.error('Failed to copy:', err);
  }
}

function notebookTitle(path: string): string {
  const filename = notebookFilename(path);
  return filename
    .replace(/\.ipynb$/i, '')
    .replace(/^\d+[-_]+/, '')
    .replace(/[-_]+/g, ' ')
    .trim()
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function notebookFilename(path: string): string {
  return path.split('/').pop() ?? path;
}
</script>

<style scoped>
.notebook-list {
  margin: 0;
  padding-left: 24px;
}

.notebook-list > li {
  margin-bottom: 8px;
}

.notebook-list > li:last-child {
  margin-bottom: 0;
}

.copy-btn {
  flex-shrink: 0;
}

.docker-command {
  flex: 1;
  min-width: 0;
  font-family: 'Roboto Mono', monospace;
  font-size: 0.875rem;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
