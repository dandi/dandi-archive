<template>
  <v-row>
    <v-col>
      <v-card
        variant="outlined"
        height="100%"
      >
        <v-card-title
          :id="name"
          class="font-weight-regular"
        >
          <v-icon class="mr-3 text-grey-lighten-1">
            {{ icon }}
          </v-icon>
          {{ name }}
        </v-card-title>
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
          class="ma-5"
        >
          <!-- Optional alternate component that will be used as a fallback if `items` is empty -->
          <slot name="emptyFallback" />
        </v-sheet>
      </v-card>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import type { PropType } from 'vue';
import {
  computed, defineComponent, getCurrentInstance,
} from 'vue';
import { useDisplay } from 'vuetify';

// The maximum amount of columns to show on a metadata card,
// regardless of how many entries there are.
const MAX_COLUMNS = 4;

export default defineComponent({
  name: 'MetadataCard',
  props: {
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
  },
  setup(props) {
    const $vuetify = computed(() => getCurrentInstance()?.proxy.$vuetify);
    const display = useDisplay();

    const borderLeftColor = computed(() => $vuetify.value?.theme.themes.light.primary);

    // Try to estimate the ideal number of columns to break the items into.
    // When viewing on a smaller screen, force the number of columns to 1.
    const columnCount = computed(
      () => (display.mdAndDown
        ? 1 : Math.min(Math.ceil(props.items.length / 2), MAX_COLUMNS)),
    );

    return { borderLeftColor, columnCount };
  },
});
</script>
