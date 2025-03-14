<template>
  <v-textarea
    v-if="isTextarea == true"
    ref="textField"
    :model-value="text"
    class="cite-as-textarea"
    hide-details="auto"
    variant="outlined"
    readonly
    v-bind="$attrs"
  >
    <template #prepend>
      <v-tooltip location="bottom">
        <template #activator="{ props: tooltipProps }">
          <v-icon
            v-bind="tooltipProps"
            @click="copyToClipboard"
          >
            mdi-content-copy
          </v-icon>
        </template>
        {{ iconHoverText }}
      </v-tooltip>
    </template>
  </v-textarea>

  <v-text-field
    v-else
    v-bind="$attrs"
    id="api-key-text"
    ref="textField"
    :model-value="text"
    hide-details="auto"
    variant="outlined"
    density="compact"
    readonly
  >
    <template #prepend>
      <v-tooltip location="bottom">
        <template #activator="{ props: tooltipProps }">
          <v-icon
            v-bind="tooltipProps"
            @click="copyToClipboard"
          >
            mdi-content-copy
          </v-icon>
        </template>
        {{ iconHoverText }}
      </v-tooltip>
    </template>
  </v-text-field>
</template>

<script setup lang="ts">
import { ref } from 'vue';

defineOptions({
  // This will prevent arbitrary props from being rendered as HTML attributes
  // v-bind="$attrs" ensures that props are ingested as vue props instead
  inheritAttrs: false,
});

const props = defineProps({
  text: {
    type: String,
    default: '',
  },
  iconHoverText: {
    type: String,
    default: 'Copy text to clipboard',
  },
  isTextarea: {
    type: Boolean,
    default: false,
  },
});

const textField = ref<HTMLElement | null>(null);

async function copyToClipboard() {
  try {
    await navigator.clipboard.writeText(props.text);
    console.log('Copied to clipboard');
  } catch (err) {
    console.error('Failed to copy:', err);
  }
}
</script>

<style>
.cite-as-textarea textarea {
  overflow: auto;
}
</style>
