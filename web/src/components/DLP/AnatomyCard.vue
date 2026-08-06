<template>
  <v-card
    prepend-icon="mdi-brain"
    variant="outlined"
    height="100%"
    :color="hasAnatomy ? undefined : 'warning'"
  >
    <template #title>
      <div class="d-flex align-center justify-space-between">
        <span>Anatomy</span>
        <v-chip
          v-if="hasAnatomy"
          size="small"
          color="success"
          variant="flat"
          prepend-icon="mdi-check-circle"
        >
          Provided
        </v-chip>
        <v-chip
          v-else
          size="small"
          color="warning"
          variant="flat"
          prepend-icon="mdi-alert-circle"
        >
          Missing
        </v-chip>
      </div>
    </template>

    <!-- Anatomy information is present -->
    <v-list
      v-if="hasAnatomy"
      :style="`column-count: ${columnCount};`"
      class="px-5 pb-4"
    >
      <div
        v-for="(item, i) in anatomy"
        :key="i"
        class="my-1 d-inline-block"
        style="width: 100%;"
      >
        <div
          class="pl-2 my-1 py-1"
          :style="`border-left: medium solid ${borderLeftColor}; line-height: 1.25`"
        >
          <v-row
            no-gutters
            class="align-center justify-space-between mr-1"
          >
            <v-col cols="9">
              <span class="text-grey-darken-3 font-weight-medium">
                {{ item.name || item.identifier || 'Unnamed region' }}
              </span>
              <br>
              <span
                v-if="item.identifier"
                class="text-caption text-grey-darken-1"
              >
                <strong>{{ ontologyName(item.identifier) }}: </strong>{{ ontologyLocalId(item.identifier) }}
              </span>
            </v-col>
            <v-col class="text-end">
              <v-btn
                v-if="ontologyLink(item.identifier)"
                icon
                size="small"
                variant="text"
                :href="ontologyLink(item.identifier)"
                target="_blank"
                rel="noopener"
                title="View in ontology lookup service"
              >
                <v-icon>mdi-open-in-new</v-icon>
              </v-btn>
            </v-col>
          </v-row>
        </div>
      </div>
    </v-list>

    <!-- Anatomy information is missing -->
    <v-card-text
      v-else
      class="pt-0"
    >
      <v-alert
        type="warning"
        variant="tonal"
        density="comfortable"
        class="mb-0"
      >
        <div class="font-weight-bold">
          No anatomical information provided.
        </div>
        <div class="text-caption mt-1">
          This Dandiset does not specify which brain regions or anatomical
          structures it covers. Adding indexed anatomy (e.g. UBERON terms) in the
          metadata editor makes this dataset discoverable by anatomical location.
        </div>
      </v-alert>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useDisplay, useTheme } from 'vuetify';

import type { PropType } from 'vue';
import type { Anatomy, SubjectMatterOfTheDataset } from '@/types/schema';

const MAX_COLUMNS = 3;

const props = defineProps({
  about: {
    type: Array as PropType<SubjectMatterOfTheDataset | undefined>,
    default: undefined,
  },
});

const theme = useTheme();
const display = useDisplay();

const borderLeftColor = computed(() => theme.current.value.colors.primary);

// Pull out only the Anatomy entries from the dataset's "about" field.
const anatomy = computed<Anatomy[]>(
  () => (props.about?.filter(
    (item): item is Anatomy => item.schemaKey === 'Anatomy',
  ) ?? []),
);

const hasAnatomy = computed(() => anatomy.value.length > 0);

const columnCount = computed(
  () => (display.mdAndDown.value
    ? 1 : Math.min(Math.ceil(anatomy.value.length / 2), MAX_COLUMNS)),
);

/**
 * Extract the ontology prefix from an identifier (e.g. "UBERON" from
 * "UBERON:0000955"), defaulting to a generic label.
 */
function ontologyName(identifier?: string): string {
  if (!identifier) {
    return 'Identifier';
  }
  const match = identifier.match(/^([A-Za-z]+)[:_]/);
  return match ? match[1].toUpperCase() : 'Identifier';
}

/**
 * Return the local part of an identifier (e.g. "0000955" from "UBERON:0000955"),
 * falling back to the full identifier when no ontology prefix is present.
 */
function ontologyLocalId(identifier?: string): string {
  if (!identifier) {
    return '';
  }
  const match = identifier.match(/^[A-Za-z]+[:_](.+)$/);
  return match ? match[1] : identifier;
}

/**
 * Build a link to an ontology term page for the given identifier.
 * Full URLs are used directly; OBO CURIEs (e.g. "UBERON:0000955") are resolved
 * to their OBO PURL (e.g. "http://purl.obolibrary.org/obo/UBERON_0000955").
 */
function ontologyLink(identifier?: string): string | undefined {
  if (!identifier) {
    return undefined;
  }
  try {
    const url = new URL(identifier);
    if (url.protocol === 'http:' || url.protocol === 'https:') {
      return identifier;
    }
  } catch {
    // Not a full URL; fall through to OBO PURL resolution.
  }
  const match = identifier.match(/^([A-Za-z]+)[:_](.+)$/);
  if (match) {
    return `http://purl.obolibrary.org/obo/${match[1]}_${match[2]}`;
  }
  return undefined;
}
</script>
