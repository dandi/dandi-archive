<template>
  <v-list-item>
    <v-list-item-action class="mr-2">
      <!-- ".stop" prevents closing the parent v-menu when this is clicked -->
      <v-btn
        icon
        @click.stop="fetch"
      >
        <v-icon>mdi-reload</v-icon>
      </v-btn>
    </v-list-item-action>
    <v-list-item-content>
      <v-text-field
        ref="apiKey"
        v-model="apiKey"
        label="API Key"
        readonly
        append-outer-icon="mdi-content-copy"
        @click:append-outer="copyToClipboard"
      />
    </v-list-item-content>
  </v-list-item>
</template>

<script>
import { girderRest } from '@/rest';

export default {
  name: 'ApiKeyItem',
  data() {
    return {
      apiKey: null,
    };
  },
  created() {
    this.fetch();
  },
  methods: {
    copyToClipboard() {
      const vTextFieldComponent = this.$refs.apiKey;
      // v-text-field provides some internal refs that we can use
      // one is "input", which is the actual <input> DOM element that it uses
      const inputElement = vTextFieldComponent.$refs.input;
      inputElement.focus();
      document.execCommand('selectAll');
      inputElement.select();
      document.execCommand('copy');
    },
    async fetch() {
      let data;
      // parentheses required for using the destructure assignment
      ({ data } = await girderRest.get(
        'api_key', {
          params: {
            // eslint-disable-next-line import/no-named-as-default-member
            userId: girderRest.user._id,
            limit: 50,
            sort: 'name',
            sortdir: 1,
          },
        },
      ));
      let [dandiKey] = data.filter((key) => key.name === 'dandicli');
      if (!dandiKey) {
        // create a key
        ({ data } = await girderRest.post('api_key', null, {
          params: {
            name: 'dandicli',
            scope: JSON.stringify(['core.data.read', 'core.data.write']),
            // days
            tokenDuration: 30,
            active: true,
          },
        }));
        dandiKey = data;
      }

      this.apiKey = dandiKey.key;
    },
  },
};
</script>
