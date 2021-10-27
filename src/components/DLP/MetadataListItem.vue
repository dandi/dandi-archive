<template>
  <div
    :class="backgroundColor"
    style="width: 100%;"
  >
    <div
      class="pl-2 my-1 py-1"
      :style="`border-left: medium solid ${borderLeftColor};
               line-height: 1.25`"
    >
      <slot />
    </div>
  </div>
</template>

<script>
import { computed, defineComponent } from '@vue/composition-api';

export default defineComponent({
  name: 'ListItem',
  props: {
    backgroundColor: {
      type: String,
      default: 'white',
    },
  },
  setup(props, ctx) {
    const { $vuetify } = ctx.root;

    const borderLeftColor = computed(() => $vuetify.theme.themes.light.primary);

    return { borderLeftColor };
  },
});
</script>
