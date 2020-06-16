<template>
  <div>
    <template v-if="schema.type === 'array'">
      <template v-if="schema.items.type === 'object'">
        <v-expansion-panels>
          <v-expansion-panel
            v-for="item in data"
            :key="item[primaryKey]"
          >
            <!-- item is an object -->
            <v-expansion-panel-header>{{ item[primaryKey] }}</v-expansion-panel-header>
            <v-expansion-panel-content>
              <v-list>
                <v-list-item
                  v-for="key in Object.keys(item).sort()"
                  :key="key"
                >
                  <!-- value's type matches that specified at schema.items.properties[key].type -->
                  <ListingComponent
                    :schema="schema.items.properties[key]"
                    :data="item[key]"
                  />
                </v-list-item>
              </v-list>
            </v-expansion-panel-content>
          </v-expansion-panel>
        </v-expansion-panels>
      </template>
      <template v-else-if="schema.items.type === 'array'">
        <!-- May not work. Not tested in a real scenario. -->
        <ListingComponent
          v-for="item in data"
          :key="item"
          :schema="schema.items"
          :data="item"
        />
      </template>
      <template v-else>
        <template v-if="!root">
          <b>{{ schema.title }}</b>:
        </template>
        {{ data.join(', ') }}
      </template>
    </template>
    <template v-else-if="schema.type === 'object'">
      <v-list dense>
        <v-list-item
          v-for="key in Object.keys(data).sort()"
          :key="key"
          dense
        >
          <ListingComponent
            :schema="schema.properties[key]"
            :data="data[key]"
          />
        </v-list-item>
      </v-list>
    </template>
    <template v-else>
      <!-- Base Case -->
      <template v-if="!root">
        <b>{{ schema.title }}</b>:
      </template>
      {{ data }}
    </template>
  </div>
</template>

<script>
export default {
  name: 'ListingComponent',
  props: {
    schema: {
      // The root schema of the item to render
      type: [Object],
      required: true,
    },
    data: {
      // The data at the matching level of schema
      type: [Object, Number, String, Array],
      required: true,
    },
    root: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    primaryKey() {
      switch (this.schema.title) {
        case 'Access':
          return 'status';
        case 'Publications':
          return 'url';
        case 'Organism':
          return 'species';
        default:
          return 'name';
      }
    },
  },
};
</script>
