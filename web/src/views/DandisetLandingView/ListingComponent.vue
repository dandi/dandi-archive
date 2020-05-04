<template>
  <div>
    <template v-if="schema.type === 'array'">
      <template v-if="schema.items.type === 'object'">
        <v-expansion-panels>
          <v-expansion-panel
            v-for="item in data"
            :key="item[schema.items.listingKey]"
          >
            <!-- item is an object -->
            <v-expansion-panel-header>{{ item[schema.items.listingKey] }}</v-expansion-panel-header>
            <v-expansion-panel-content>
              <v-list>
                <v-list-item
                  v-for="(value, key) in item"
                  :key="key"
                >
                  <!-- value's type matches that specified at schema.items.properties[key].type -->
                  <ListingComponent
                    :schema="schema.items.properties[key]"
                    :data="value"
                  />
                </v-list-item>
              </v-list>
            </v-expansion-panel-content>
          </v-expansion-panel>
        </v-expansion-panels>
      </template>
      <template v-else>
        <b>{{ schema.title }}</b>: {{ data.join(', ') }}
      </template>
    </template>
    <template v-else-if="schema.type === 'object'">
      <v-list>
        <v-list-item
          v-for="(value, key) in data"
          :key="key"
        >
          <ListingComponent
            :schema="schema.properties[key]"
            :data="value"
          />
        </v-list-item>
      </v-list>
    </template>
    <template v-else>
      <!-- Base Case -->
      <b>{{ schema.title }}</b>: {{ data }}
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
  },
};
</script>
