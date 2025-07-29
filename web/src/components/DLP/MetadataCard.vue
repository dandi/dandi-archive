<template>
  <v-card
    :prepend-icon="icon"
    variant="outlined"
    height="100%"
  >
    <template
      :id="name"
      v-slot:title
    >
      <span>{{ name }}</span>
    </template>
    <v-list
      v-if="items && items.length"
      :style="`column-count: ${columnCount};`"
      class="px-5"
    >
      <div
        v-for="(item, i) in items"
        :key="i"
      >
        <div
          :class="`my-1 d-inline-block ${backgroundColor}`"
          style="width: 100%;"
        >
          <div
            class="pl-2 my-1 py-1"
            :style="`border-left: medium solid ${borderLeftColor};
                   line-height: 1.25`"
          >
            <v-row
              no-gutters
              class="justify-space-between mr-4"
            >
              <v-col
                cols="9"
                class="text-grey-darken-3"
              >
                <span v-if="item.name || item.identifier || item.id">
                  {{ item.name || item.identifier || item.id }}
                  <br>
                </span>
                <slot
                  name="content"
                  :item="item"
                />
              </v-col>

              <v-col class="px-1 text-end font-weight-light">
                <slot
                  name="links"
                  :item="item"
                />
              </v-col>
            </v-row>
          </div>
        </div>
      </div>
    </v-list>
    <v-sheet
      v-else
      class="mx-5 mt-1 mb-4 pa-0"
    >
      <!-- Optional alternate component that will be used as a fallback if `items` is empty -->
      <slot name="emptyFallback" />
    </v-sheet>
  </v-card>
</template>

<script setup lang="ts">
import type { PropType } from 'vue';
import { computed } from 'vue';
import { useDisplay, useTheme } from 'vuetify';

// The maximum amount of columns to show on a metadata card,
// regardless of how many entries there are.
const MAX_COLUMNS = 4;


const props = defineProps({
  backgroundColor: {
    type: String,
    default: 'white',
  },
  items: {
    type: Array as PropType<any[]>,
    required: true,
  },
  name: {
    type: String,
    required: true,
  },
  icon: {
    type: String,
    required: true,
  },
});

const theme = useTheme();
const display = useDisplay();

const borderLeftColor = computed(() => theme.current.value.colors.primary);

// Try to estimate the ideal number of columns to break the items into.
// When viewing on a smaller screen, force the number of columns to 1.
const columnCount = computed(
  () => (display.mdAndDown.value
    ? 1 : Math.min(Math.ceil(props.items.length / 2), MAX_COLUMNS)),
);
</script>
