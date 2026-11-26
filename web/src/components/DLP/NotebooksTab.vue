<template>
  <div v-if="notebooks">
    <v-card variant="outlined">
      <v-card-title class="d-flex align-center pt-4 px-4">
        <v-icon
          color="primary"
          class="mr-2"
        >
          mdi-notebook-outline
        </v-icon>
        Notebooks
      </v-card-title>
      <v-card-subtitle class="px-4 pb-3 notebooks-intro">
        Jupyter notebooks that load and analyze this Dandiset, from
        <a
          :href="notebooks.siteUrl"
          target="_blank"
          rel="noopener"
          class="text-primary"
        >DANDI Notebooks<v-icon
          size="x-small"
          class="ml-1"
        >mdi-open-in-new</v-icon></a>
      </v-card-subtitle>
      <v-divider />

      <template
        v-for="group in groupedNotebooks"
        :key="group.key"
      >
        <!-- The folder the notebooks are in on DANDI Notebooks -->
        <div
          v-if="group.segments.length"
          class="notebook-group px-4 pt-4 pb-1"
        >
          {{ group.segments.join(' › ') }}
        </div>

        <ul class="notebook-list">
          <li
            v-for="notebook in group.notebooks"
            :key="notebook.path"
            class="notebook-row"
          >
            <!-- Name on the left, actions on the right; below sm the actions
                 go under the name. -->
            <div class="d-flex flex-column flex-sm-row align-sm-center ga-2 ga-sm-4 px-4 py-3">
              <div
                class="d-flex align-center ga-3 flex-grow-1"
                style="min-width: 0;"
              >
                <v-icon
                  color="primary"
                  class="flex-shrink-0"
                >
                  mdi-notebook-outline
                </v-icon>
                <div style="min-width: 0;">
                  <div class="text-body-1 font-weight-medium">
                    {{ notebookTitle(notebook.path) }}
                  </div>
                  <div
                    class="text-caption text-medium-emphasis notebook-filename text-truncate"
                    :title="notebook.path"
                  >
                    {{ notebookFilename(notebook.path) }}
                  </div>
                </div>
              </div>

              <div class="d-flex align-center flex-wrap ga-2 flex-shrink-0 notebook-actions">
                <v-btn
                  v-if="notebook.colab_url"
                  :href="notebook.colab_url"
                  target="_blank"
                  rel="noopener"
                  size="small"
                  variant="tonal"
                  color="primary"
                  class="text-none notebook-action"
                >
                  <template #prepend>
                    <img
                      :src="COLAB_ICON"
                      alt=""
                      width="16"
                      height="16"
                    >
                  </template>
                  <!-- Shorter on phones, so all three actions fit on one row. -->
                  {{ isXsDisplay ? 'Colab' : 'Open in Colab' }}
                </v-btn>
                <v-btn
                  :href="notebook.github_url"
                  target="_blank"
                  rel="noopener"
                  size="small"
                  variant="outlined"
                  prepend-icon="mdi-github"
                  class="text-none notebook-action"
                >
                  GitHub
                </v-btn>
                <v-btn
                  v-if="notebook.docker_command"
                  size="small"
                  variant="outlined"
                  prepend-icon="mdi-docker"
                  :append-icon="expanded === notebook.path ? 'mdi-chevron-up' : 'mdi-chevron-down'"
                  :aria-expanded="expanded === notebook.path"
                  class="text-none notebook-action"
                  @click="toggleDocker(notebook.path)"
                >
                  Docker
                </v-btn>
              </div>
            </div>

            <v-expand-transition>
              <!-- pl-13 lines the panel up with the notebook name, past its icon. -->
              <div
                v-show="expanded === notebook.path"
                class="pl-4 pl-sm-13 pr-4 pb-3"
              >
                <div class="docker-command d-flex align-center ga-2 rounded">
                  <code class="flex-1-1-0">{{ notebook.docker_command }}</code>
                  <v-btn
                    icon
                    size="small"
                    variant="text"
                    class="flex-shrink-0"
                    :aria-label="copied === notebook.path ? 'Copied' : 'Copy the Docker command'"
                    @click="copyDockerCommand(notebook)"
                  >
                    <v-icon size="small">
                      {{ copied === notebook.path ? 'mdi-check' : 'mdi-content-copy' }}
                    </v-icon>
                    <v-tooltip
                      activator="parent"
                      location="top"
                    >
                      {{ copied === notebook.path ? 'Copied!' : 'Copy the Docker command' }}
                    </v-tooltip>
                  </v-btn>
                </div>
                <a
                  :href="notebooks.dockerHelpUrl"
                  target="_blank"
                  rel="noopener"
                  class="text-caption text-primary d-inline-block mt-1"
                >How to run DANDI Notebooks with Docker<v-icon
                  size="x-small"
                  class="ml-1"
                >mdi-open-in-new</v-icon></a>
              </div>
            </v-expand-transition>
          </li>
        </ul>
      </template>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useDisplay } from 'vuetify';

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

// Colab's own icon, so the button is recognizable at a glance.
const COLAB_ICON = 'https://colab.research.google.com/img/colab_favicon_256px.png';

const display = useDisplay();
const isXsDisplay = computed(() => display.xs.value);

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
.notebooks-intro {
  white-space: normal;
  opacity: 1;
  color: rgba(0, 0, 0, 0.6);
}
.notebook-group {
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: rgba(0, 0, 0, 0.6);
}
.notebook-list {
  list-style: none;
}
.notebook-row + .notebook-row {
  border-top: thin solid rgba(0, 0, 0, 0.08);
}
.notebook-row:hover {
  background: rgba(0, 0, 0, 0.02);
}
.notebook-filename {
  font-family: monospace;
}
.docker-command {
  background: rgba(0, 0, 0, 0.05);
  padding: 4px 4px 4px 12px;
}
.docker-command code {
  background: none;
  font-size: 0.8125rem;
  /* Wrap on narrow screens; the copy button copies it whole. */
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.notebook-action {
  letter-spacing: normal;
}
</style>
