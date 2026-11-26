<template>
  <div
    class="d-flex justify-center align-center text-center"
  >
    <v-btn
      :class="isXsDisplay ? 'mx-1' : 'mx-2'"
      :min-width="isXsDisplay ? 44 : undefined"
      color="white"
      :disabled="page === 1 || !pageIsValid(page)"
      @click="emit('changePage', 1)"
    >
      <v-icon>mdi-chevron-double-left</v-icon>
    </v-btn>
    <v-btn
      :class="isXsDisplay ? 'mx-1' : 'mx-2'"
      :min-width="isXsDisplay ? 44 : undefined"
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
      density="compact"
      style="max-width: max(5%, 3.5rem); min-width: 3.5rem;"
      class="pa-0 mx-2 my-0"
      variant="filled"
      min="1"
      :max="pageCount"
      :maxlength="pageCount"
      :rules="[pageIsValid]"
      @change="emit('changePage', pageInput)"
    />

    <span class="text-no-wrap">of {{ pageCount }}</span>
    <v-btn
      :class="isXsDisplay ? 'mx-1' : 'mx-2'"
      :min-width="isXsDisplay ? 44 : undefined"
      color="white"
      :disabled="page === pageCount || !pageIsValid(page)"
      @click="emit('changePage', page + 1)"
    >
      <v-icon>mdi-chevron-right</v-icon>
    </v-btn>
    <v-btn
      :class="isXsDisplay ? 'mx-1' : 'mx-2'"
      :min-width="isXsDisplay ? 44 : undefined"
      color="white"
      :disabled="page === pageCount || !pageIsValid(page)"
      @click="emit('changePage', pageCount)"
    >
      <v-icon>mdi-chevron-double-right</v-icon>
    </v-btn>
  </div>
</template>

<script setup lang="ts">
import { computed, toRef } from 'vue';
import { useRoute } from 'vue-router';
import { useDisplay } from 'vuetify';

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
const display = useDisplay();
const isXsDisplay = computed(() => display.xs.value);

function pageIsValid(page: number): boolean {
  return page > 0 && page <= props.pageCount;
}

const emit = defineEmits(['changePage']);

const pageInput = Number(route.query.page) || toRef(props, 'page');

</script>
