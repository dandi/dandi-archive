<template>
  <v-textarea
    v-if="isTextarea == true"
    ref="textField"
    :value="text"
    hide-details="auto"
    auto-grow
    outlined
    dense
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
    ref="textField"
    :value="text"
    hide-details="auto"
    outlined
    dense
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
  </v-text-field>
</template>

<script>
export default {
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
      type: String,
      default: 'is-textarea',
    },
  },
  data() {
    return {
      messages: [],
    };
  },
  methods: {
    copyToClipboard() {
      const vTextFieldComponent = this.$refs.textField;
      // v-text-field provides some internal refs that we can use
      // one is "input", which is the actual <input> DOM element that it uses
      const inputElement = vTextFieldComponent.$refs.input;
      inputElement.focus();
      document.execCommand('selectAll');
      inputElement.select();
      document.execCommand('copy');

      // Notify the user that the copy was successful
      this.messages.push('Copied!');
      // Remove the notification after 4 seconds
      setTimeout(() => this.messages.pop(), 4000);
    },
  },
};
</script>
