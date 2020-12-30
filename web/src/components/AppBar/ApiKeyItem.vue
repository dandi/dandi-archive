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
      <CopyText
        :text="apiKey"
        label="API Key"
        icon-hover-text="Copy API key to clipboard"
      />
    </v-list-item-content>
  </v-list-item>
</template>

<script>
import CopyText from '@/components/CopyText.vue';
import { girderRest, publishRest } from '@/rest';
import toggles from '@/featureToggle';

export default {
  name: 'ApiKeyItem',
  components: {
    CopyText,
  },
  data() {
    return {
      apiKey: null,
    };
  },
  created() {
    this.fetch();
  },
  methods: {
    async fetch() {
      if (toggles.DJANGO_API) {
        this.apiKey = await publishRest.apiKey();
      } else {
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
              scope: null,
              // days
              tokenDuration: 30,
              active: true,
            },
          }));
          dandiKey = data;
        }

        this.apiKey = dandiKey.key;
      }
    },
  },
};
</script>
