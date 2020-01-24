<template>
  <div>
    <h1>DANDI Metadata</h1>
    <v-container>
      <template v-for="(item, key) in meta">
        <v-row :key="key">
          <v-col cols="3">
            <v-card :key="key">
              <v-card-title>
                {{key}}
              </v-card-title>
              <v-card-text>
                <v-textarea
                  v-if="typeof item === 'object'"
                  :value="JSON.stringify(item, null, 2)"
                  @input="setMetaObject($event, key)"
                  :error-messages="errors[key] ? [errors[key]] : null"
                  auto-grow
                  solo
                  flat
                />
                <v-text-field v-else v-model="meta[key]" solo flat />
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
import { debounce } from 'lodash';

export default {
  props: ['id'],
  components: {},
  data() {
    return {
      meta: {},
      errors: {},
    };
  },
  computed: {
    valid() {
      return !Object.keys(this.errors).length;
    },
    ...mapState({
      selected: state => (state.selected.length === 1 ? state.selected[0] : undefined),
      girderRest: 'girderRest',
    }),
  },
  watch: {
    selected(val) {
      if (!val || !val.meta || !val.meta.dandiset) {
        this.meta = {};
      } else {
        this.meta = { ...val.meta.dandiset };
      }
    },
    valid: debounce(function debouncedValid(valid) {
      if (valid) {
        this.saveDandiMeta();
      }
    }, 1000),
  },
  methods: {
    saveDandiMeta() {
      this.girderRest.put(`/folder/${this.id}/metadata`, { dandiset: this.meta }, { params: { allowNull: false } });
    },
    setMetaObject(val, index) {
      try {
        this.$set(this.meta, index, JSON.parse(val));
        this.$delete(this.errors, index);
      } catch (err) {
        this.$set(this.errors, index, err.message);
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
