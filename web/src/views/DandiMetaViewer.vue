<template>
  <div>
    <h1>DANDI Metadata</h1>
    <v-container>
      <template v-for="(item, i) in meta">
        <v-row :key="i">
          <v-col cols="3">
            <v-card :key="item.name">
              <v-card-title>
                {{item.name}}
              </v-card-title>
              <v-card-text>
                <v-textarea
                  v-if="typeof item.value === 'object'"
                  :value="JSON.stringify(item.value, null, 2)"
                  @input="setMetaObject($event, i)"
                  :error="checkError(i)"
                  solo
                  flat
                />
                <v-text-field v-else v-model="meta[i].value" solo flat />
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </template>
    </v-container>
  </div>
</template>

<script>
import { mapState } from 'vuex';

export default {
  props: ['id'],
  components: {},
  data() {
    return {
      meta: [],
      errors: {},
    };
  },
  computed: {
    ...mapState({
      selected: state => (state.selected.length === 1 ? state.selected[0] : undefined),
      girderRest: 'girderRest',
    }),
  },
  watch: {
    selected(val) {
      if (!val || !val.meta) {
        this.meta = [];
      } else {
        this.meta = Object.keys(val.meta).map(k => ({
          name: k,
          value: this.selected.meta[k],
        }));
      }

      // TODO: Fix reactivity
      // const _this = this;
      // Object.keys(this.meta).forEach((x) => {
      //   this.$set(_this.meta, x, this.meta[x]);
      // });
    },
    meta(val) {
      console.log('Meta changed', val);
    },
  },
  methods: {
    checkError(index) {
      return index in this.errors;
    },
    setMetaObject(val, index) {
      // TODO: Fix textareas not showing errors
      try {
        this.meta[index] = JSON.parse(val);
        delete this.errors[index];
      } catch (err) {
        this.errors[index] = err.message;
      }
    },
  },
  async created() {
    if (!this.selected || !this.meta.length) {
      const resp = await this.girderRest.get(`folder/${this.id}`);
      this.$store.commit('setSelected', [resp.data]);
    }
  },
};
</script>

<style>

</style>
