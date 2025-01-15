<template>
  <div
    class="d-flex justify-center align-center text-center"
  >
    <v-btn
      class="mx-2"
      color="white"
      :disabled="page === 1 || !pageIsValid(page)"
      @click="emit('changePage', 1)"
    >
      <v-icon>mdi-chevron-double-left</v-icon>
    </v-btn>
    <v-btn
      class="mx-2"
      color="white"
      :disabled="page === 1 || !pageIsValid(page)"
      @click="emit('changePage', page - 1)"
    >
      <v-icon>mdi-chevron-left</v-icon>
    </v-btn>
    <v-text-field
      v-model.number="pageInput"
      hide-details
      single-line
      dense
      style="max-width: 5%;"
      class="pa-0 mx-2 my-0"
      filled
      min="1"
      :max="pageCount"
      :maxlength="pageCount"
      :rules="[pageIsValid]"
      @change="emit('changePage', pageInput)"
    />

    <span>of {{ pageCount }}</span>
    <v-btn
      class="mx-2"
      color="white"
      :disabled="page === pageCount || !pageIsValid(page)"
      @click="emit('changePage', page + 1)"
    >
      <v-icon>mdi-chevron-right</v-icon>
    </v-btn>
    <v-btn
      class="mx-2"
      color="white"
      :disabled="page === pageCount || !pageIsValid(page)"
      @click="emit('changePage', pageCount)"
    >
      <v-icon>mdi-chevron-double-right</v-icon>
    </v-btn>
  </div>
</template>

<script setup lang="ts">
import { toRef } from 'vue';
import { useRoute } from 'vue-router';

const props = defineProps({
  page: {
    type: Number,
    required: true,
  },
  pageCount: {
    type: Number,
    required: true,
  },
});

const route = useRoute();

function pageIsValid(page: number): boolean {
  return page > 0 && page <= props.pageCount;
}

const emit = defineEmits(['changePage']);

const pageInput = Number(route.query.page) || toRef(props, 'page');

</script>
