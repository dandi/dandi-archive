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
      v-model="pageInput"
      hide-details
      single-line
      type="number"
      dense
      style="max-width: 5%;"
      class="pa-0 mx-2 my-0"
      filled
      min="1"
      :max="pageCount"
      :maxlength="pageCount"
      :rules="[pageIsValid]"
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
import { ref, watch } from 'vue';

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

function pageIsValid(page: number): boolean {
  return page > 0 && page <= props.pageCount;
}

const emit = defineEmits(['changePage']);

// Note: the v-textfield `v-model` returns a string value despite its type being 'number', so
// we have to handle converting back and forth below.
const pageInput = ref(props.page.toString());

watch(() => props.page, (newPage) => { pageInput.value = newPage.toString(); });
watch(pageInput, (newPage) => emit('changePage', Number(newPage)));
</script>
