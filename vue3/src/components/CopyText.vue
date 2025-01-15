<template>
  <v-textarea
    v-if="isTextarea == true"
    ref="textField"
    :value="text"
    class="cite-as-textarea"
    hide-details="auto"
    outlined
    readonly
    :success-messages="messages"
    v-bind="$attrs"
  >
    <template #prepend>
      <v-tooltip bottom>
        <template #activator="{ on }">
          <v-icon
            v-on="on"
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
    :value="text"
    hide-details="auto"
    outlined
    dense
    readonly
    :success-messages="messages"
  >
    <template #prepend>
      <v-tooltip bottom>
        <template #activator="{ on }">
          <v-icon
            v-on="on"
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

<script lang="ts">
import type { Ref } from 'vue';
import { defineComponent, ref } from 'vue';

export default defineComponent({
  name: 'ApiKeyItem',
  // This will prevent arbitrary props from being rendered as HTML attributes
  // v-bind="$attrs" ensures that props are ingested as vue props instead
  inheritAttrs: false,
  props: {
    text: {
      type: String,
      // not required because the data will frequently default to null prior to loading
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
  },
  setup() {
    const messages: Ref<string[]> = ref([]);
    const textField = ref(null);

    function copyToClipboard() {
      // v-text-field provides some internal refs that we can use
      // one is "input", which is the actual <input> DOM element that it uses
      // @ts-ignore
      const inputElement = textField.value.$refs.input;
      inputElement.focus();
      document.execCommand('selectAll');
      inputElement.select();
      document.execCommand('copy');

      // Notify the user that the copy was successful
      messages.value.push('Copied!');
      // Remove the notification after 4 seconds
      setTimeout(() => messages.value.pop(), 4000);
    }

    return {
      messages,
      copyToClipboard,
      textField,
    };
  },
});
</script>

<style>
.cite-as-textarea textarea {
  overflow: auto;
}
</style>
