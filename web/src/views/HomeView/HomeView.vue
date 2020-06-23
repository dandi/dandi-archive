<template>
  <v-container
    fluid
    class="pa-0"
  >
    <v-row>
      <v-img
        src="@/assets/logo.svg"
        class="grey lighten-5"
        position="left"
        max-height="500px"
        contain
      >
        <v-container
          fluid
          class="d-flex flex-column py-0"
          :class="[$vuetify.breakpoint.smAndUp ? 'brain-gradient' : 'hide-brain']"
        >
          <v-row class="flex-grow-0">
            <v-alert
              border="bottom"
              class="flex-grow-1 mb-0 text-center"
              color="light-blue lighten-5 light-blue--text text--darken-1"
            >
              <v-icon color="light-blue darken-1">
                mdi-information
              </v-icon>
              We're in early access
            </v-alert>
          </v-row>
          <v-row
            class="flex-grow-1"
            justify="center"
            align="center"
          >
            <v-col class="splash-text my-12">
              <div class="text-h2 font-weight-thin text-center light-blue--text text--darken-1">
                The DANDI Archive
              </div>
              <div class="text-h6 font-weight-light text-center">
                The BRAIN Initiative archive for publishing and sharing
                cellular neurophysiology data
              </div>
            </v-col>
          </v-row>
        </v-container>
      </v-img>
    </v-row>
    <v-row class="flex-grow-0">
      <StatsBar />
    </v-row>
    <v-row no-gutters>
      <v-col class="grey darken-2 pa-12">
        <DandisetSearchField :dense="false" />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import StatsBar from '@/views/HomeView/StatsBar.vue';
import DandisetSearchField from '@/components/DandisetSearchField.vue';

export default {
  name: 'HomeView',
  components: { StatsBar, DandisetSearchField },
  created() {
    this.$store.dispatch('stats/reload');
  },
};
</script>

<style scoped>
.brain-gradient {
  height: 100%;
  background-image: linear-gradient(
    to right,
    rgba(250, 250, 250, 0.85),
    rgba(250, 250, 250, 1),
    rgba(250, 250, 250, 1),
    rgba(250, 250, 250, 1)
  );
}

.hide-brain {
  height: 100%;
  background-image: linear-gradient(
    to right,
    rgba(250, 250, 250, 1),
    rgba(250, 250, 250, 1)
  );
}

.splash-text {
  max-width: 560px;
}
</style>
