<template>
  <v-list
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
              class="grey--text text--darken-3"
            >
              {{ item.name }}
              <br>
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
</template>

<script>
import { computed, defineComponent } from '@vue/composition-api';

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
      type: Array,
      required: true,
    },
  },
  setup(props, ctx) {
    const { $vuetify } = ctx.root;

    const borderLeftColor = computed(() => $vuetify.theme.themes.light.primary);

    const columnCount = computed(() => Math.min(Math.ceil(props.items.length / 2), MAX_COLUMNS));

    return { borderLeftColor, columnCount };
  },
});
</script>
